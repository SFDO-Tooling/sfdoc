from calendar import timegm
from datetime import datetime
from http import HTTPStatus
from urllib.parse import urljoin
from urllib.parse import urlparse

from django.conf import settings
import jwt
import requests
from simple_salesforce import Salesforce as SimpleSalesforce
from simple_salesforce import exceptions as SimpleSalesforceExceptions

from .exceptions import SalesforceError
from .html import HTML
from .models import Article

from .logger import get_logger
from logging import getLogger

query_logger = getLogger("query_str")


class SalesforceArticles:
    """A docset-scoped or unscoped view of Salesforce Knowledge articles"""

    ALL_DOCSETS = ("#ALL",)  # token to represent a view that is not filtered by docset
    # class variables
    api = None
    _article_info_cache = {}

    def __init__(self, docset_uuid):
        """Create a docset-scoped or unscoped view of Salesforce Knowledge articles"""
        if not self.api:
            self._get_salesforce_api()
        self.docset_uuid = docset_uuid
        self._sf_docset = None

    @classmethod
    def _get_salesforce_api(cls):
        """Get an instance of the Salesforce REST API."""
        url = settings.SALESFORCE_LOGIN_URL
        if settings.SALESFORCE_SANDBOX:
            url = url.replace('login', 'test')
        payload = {
            'alg': 'RS256',
            'iss': settings.SALESFORCE_CLIENT_ID,
            'sub': settings.SALESFORCE_USERNAME,
            'aud': url,
            'exp': timegm(datetime.utcnow().utctimetuple()),
        }
        encoded_jwt = jwt.encode(
            payload,
            settings.SALESFORCE_JWT_PRIVATE_KEY,
            algorithm='RS256',
        )
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': encoded_jwt,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        auth_url = urljoin(url, 'services/oauth2/token')
        response = requests.post(url=auth_url, data=data, headers=headers)
        response.raise_for_status()  # maybe VPN or auth problem!
        response_data = response.json()
        sf = SimpleSalesforce(
            instance_url=response_data['instance_url'],
            session_id=response_data['access_token'],
            sandbox=settings.SALESFORCE_SANDBOX,
            version=settings.SALESFORCE_API_VERSION,
            client_id='sfdoc',
        )
        cls.api = sf

    def get_docsets(self):
        query_str = f"""SELECT Id, {settings.SALESFORCE_DOCSET_ID_FIELD},
                    Index_Article_Id__c
                    FROM {settings.SALESFORCE_DOCSET_SOBJECT}"""
        return self.api.query(query_str)["records"]

    def archive(self, kav_id):
        """Archive a published article."""
        # Ensure that this article is owned by the right docset
        article = self.get_by_kav_id(kav_id, "online")

        ka_id = article["KnowledgeArticleId"]

        docset_id = article[self.docset_relation][settings.SALESFORCE_DOCSET_ID_FIELD]
        assert docset_id == self.docset_uuid

        draft = self.article_info_cache('draft', KnowledgeArticleId=ka_id)

        # delete draft if it exists
        if draft:
            assert len(draft) == 1
            self.delete(draft[0]['Id'])
        # archive published version
        self.set_publish_status(kav_id, 'archived')

    def _ensure_sf_docset_object_exists(self):
        sf_docset_api = getattr(self.api, settings.SALESFORCE_DOCSET_SOBJECT)

        try:
            self._sf_docset = sf_docset_api.get_by_custom_id(settings.SALESFORCE_DOCSET_ID_FIELD, self.docset_uuid)
        except SimpleSalesforceExceptions.SalesforceResourceNotFound:
            data = {settings.SALESFORCE_DOCSET_ID_FIELD: self.docset_uuid,
                    settings.SALESFORCE_DOCSET_STATUS_FIELD: settings.SALESFORCE_DOCSET_STATUS_INACTIVE
                    }
            sf_docset_api.create(data)
            self._sf_docset = sf_docset_api.get_by_custom_id(settings.SALESFORCE_DOCSET_ID_FIELD, self.docset_uuid)
        return self._sf_docset

    @property
    def sf_docset(self):
        return self._sf_docset or self._ensure_sf_docset_object_exists()

    def query(self, querystr, *args):
        return self.api_query(querystr.format(*args))

    def create_article(self, html):
        """Create a new article in draft state."""
        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        data = html.create_article_data()
        data[settings.SALESFORCE_DOCSET_RELATION_FIELD] = self.sf_docset['Id']
        result = kav_api.create(data=data)
        kav_id = result['id']
        self.invalidate_cache()     # I would prefer to update the cache but I
        #                             would need to do a query to get the
        #                             KnowledgeArticleId anyways. :(
        return kav_id

    def create_draft(self, ka_id):
        """Create a draft copy of a published article."""
        self.invalidate_cache()
        url = (
            self.api.base_url +
            'knowledgeManagement/articleVersions/masterVersions'
        )
        data = {'articleId': ka_id}
        result = self.api._call_salesforce('POST', url, json=data)
        if result.status_code != HTTPStatus.CREATED:
            e = SalesforceError((
                'Error creating new draft for KnowlegeArticle (ID={})'
            ).format(ka_id))
            raise(e)
        kav_id = result.json()['id']
        return kav_id

    def delete(self, kav_id):
        """Delete a KnowledgeArticleVersion."""
        self.invalidate_cache()
        url = (
            self.api.base_url +
            'knowledgeManagement/articleVersions/masterVersions/{}'
        ).format(kav_id)
        result = self.api._call_salesforce('DELETE', url)
        if result.status_code != HTTPStatus.NO_CONTENT:
            raise SalesforceError((
                'Error deleting KnowledgeArticleVersion (ID={})'
            ).format(kav_id))

    def get_by_kav_id(self, kav_id, publish_status):
        try:
            return self.article_info_cache(publish_status, Id=kav_id)[0]
        except IndexError:
            raise SalesforceError(
                'KnowledgeArticleVersion {} not found'.format(kav_id)
            )

    def get_ka_id(self, kav_id, publish_status):
        """Get KnowledgeArticleId from KnowledgeArticleVersion Id."""
        kav = self.get_by_kav_id(kav_id, publish_status)
        return kav["KnowledgeArticleId"]

    def get_articles(self, publish_status):
        """Get all article versions with a given publish status."""
        return self.article_info_cache(publish_status)

    def query_articles(self, fields, filters={}, *, include_wrapper=False,
                       object_type=settings.SALESFORCE_ARTICLE_TYPE):
        query_str = "SELECT "
        query_str += ",".join(fields)
        query_str += " FROM "
        query_str += object_type

        if self.docset_scoped:
            filters[self.docset_uuid_join_field] = self.docset_uuid

        if filters:
            query_str += " WHERE "

        query_str += ' AND '.join(f"{fieldname}='{value}'"
                                  for fieldname, value in filters.items())

        query_logger.info("QUERY: %s", query_str)
        result = self.api.query(query_str)
        query_logger.info("RESULT: %s", repr(result))

        assert result['totalSize'] == len(result['records'])
        if include_wrapper:
            return result
        else:
            return result['records']

    @property
    def docset_relation(self):
        return settings.SALESFORCE_DOCSET_SOBJECT.replace("__c", "__r")

    @property
    def docset_uuid_join_field(self):
        return f"{self.docset_relation}.{settings.SALESFORCE_DOCSET_ID_FIELD}"

    def get_base_url(self):
        """ Return base URL e.g. https://powerofus.force.com """
        o = urlparse(self.api.base_url)

        domain = '{}.force.com'.format(settings.SALESFORCE_COMMUNITY)

        if settings.SALESFORCE_SANDBOX:
            parts = o.netloc.split('.')
            instance = parts[1]
            sandbox_name = parts[0].split('--')[1]

            domain = '{}-{}.{}.force.com'.format(
                sandbox_name,
                settings.SALESFORCE_COMMUNITY,
                instance
            )

        return '{}://{}'.format(
            o.scheme,
            domain,
        )

    def get_preview_url(self, ka_id, online=False):
        """Article preview URL."""
        preview_url = (
            '{}{}'
            '?id={}&preview=true&pubstatus=d&channel=APP'
        ).format(
            self.get_base_url(),
            settings.SALESFORCE_ARTICLE_PREVIEW_URL_PATH_PREFIX,
            ka_id[:15],  # reduce to 15 char ID
        )
        if online:
            preview_url += '&pubstatus=o'
        return preview_url

    def process_draft(self, html, bundle):
        """Create a draft KnowledgeArticleVersion."""
        logger = get_logger(bundle)

        # update links to draft versions
        html.update_links_draft(bundle.docset_id, self.get_base_url())

        # query for existing article
        result_draft = self.find_articles_by_name(html.url_name, 'draft')
        result_online = self.find_articles_by_name(html.url_name, 'online')

        if len(result_draft) == 1:
            # draft exists, update fields
            kav_id = result_draft[0]['Id']
            self.update_draft(kav_id, html)
            if len(result_online) == 1:
                # published version exists
                status = Article.STATUS_CHANGED
            else:
                # not published
                status = Article.STATUS_NEW
            logger.info("Draft updated with DB status %s, %s", status, html.url_name)
        elif len(result_online) == 0:
            # new draft, new article
            kav_id = self.create_article(html)
            status = Article.STATUS_NEW
            logger.info("Draft created with DB status %s, %s", status, html.url_name)
        elif len(result_online) == 1:
            # new draft of existing article
            record = result_online[0]
            # check for changes in article fields
            if html.same_as_record(record):
                # no update
                logger.info("Draft did not change: skipping: %s", html.url_name)
                return
            # create draft copy of published article
            kav_id = self.create_draft(record['KnowledgeArticleId'])
            self.update_draft(kav_id, html)
            status = Article.STATUS_CHANGED
            logger.info("New draft of published article, status %s, %s", status, html.url_name)

        self.save_article(kav_id, html, bundle, status)

    #  As with all caches, be careful with this one.
    #  Several things have bitten me with it already.
    #  1. You MUST specify a publish_status in the query. Draft records go missing if you don't.
    #  2. If you don't manage it as a class variable, you could get two different out-of-sync views of the data.
    #  3. If the data changes remotely while you have an open Salesforce docset view, you're hooped, obviously.
    def article_info_cache(self, publish_status, **filters):
        publish_status = publish_status.lower()
        key = (self.docset_uuid, publish_status)
        if not self._article_info_cache.get(key):
            fields = ["Id", "KnowledgeArticleId", "Title", "Summary", "IsVisibleInCsp",
                            "IsVisibleInPkb", "IsVisibleInPrm", "UrlName", "PublishStatus",
                            settings.SALESFORCE_ARTICLE_BODY_FIELD,
                            settings.SALESFORCE_ARTICLE_AUTHOR_FIELD,
                            settings.SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD,
                            self.docset_uuid_join_field]
            where_clauses = {"language": "en_US",
                             "PublishStatus": publish_status}

            if self.docset_scoped:
                where_clauses[self.docset_uuid_join_field] = self.docset_uuid

            self._article_info_cache[key] = self.query_articles(fields, where_clauses)

        def match(item):
            return all(item[fieldname] == value for fieldname, value in filters.items())

        return [a for a in self._article_info_cache[key] if match(a)]

    @classmethod
    def invalidate_cache(cls):
        cls._article_info_cache = {}

    def publish_draft(self, kav_id):
        """Publish a draft KnowledgeArticleVersion."""
        assert self.docset_scoped, "Need docset scoping to publish safely"
        kav = self.get_by_kav_id(kav_id, "draft")
        body = kav[settings.SALESFORCE_ARTICLE_BODY_FIELD]
        body = HTML.update_links_production(body)
        assert settings.AWS_S3_DRAFT_IMG_DIR not in body

        data = {settings.SALESFORCE_ARTICLE_BODY_FIELD: body}

        if settings.SALESFORCE_ARTICLE_TEXT_INDEX_FIELD is not False:
            data[settings.SALESFORCE_ARTICLE_TEXT_INDEX_FIELD] = body

        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        kav_api.update(kav_id, data)
        self.set_publish_status(kav_id, 'online')

    def find_articles_by_name(self, url_name, publish_status):
        """Query KnowledgeArticleVersion objects."""
        return self.article_info_cache(publish_status, UrlName=url_name)

    def find_article_by_name(self, url_name, publish_status):
        return self.find_articles_by_name(url_name, publish_status)[0]

    def save_article(self, kav_id, html, bundle, status):
        """Create an Article object from parsed HTML."""
        ka_id = self.get_ka_id(kav_id, 'draft')
        logger = get_logger(bundle)
        logger.info('URL -- base - %s', self.get_base_url())
        logger.info('URL -- prefix - %s', settings.SALESFORCE_ARTICLE_PREVIEW_URL_PATH_PREFIX)
        logger.info('URL -- id - %s', ka_id)
        logger.info('URL -- result - %s', self.get_preview_url(ka_id))
        Article.objects.create(
            bundle=bundle,
            ka_id=ka_id,
            kav_id=kav_id,
            preview_url=self.get_preview_url(ka_id),
            status=status,
            title=html.title,
            url_name=html.url_name,
        )

    def set_publish_status(self, kav_id, status):
        url = (
            self.api.base_url +
            'knowledgeManagement/articleVersions/masterVersions/{}'
        ).format(kav_id)
        data = {'publishStatus': status}
        self.invalidate_cache()
        result = self.api._call_salesforce('PATCH', url, json=data)
        if result.status_code != HTTPStatus.NO_CONTENT:
            raise SalesforceError((
                'Error setting status={} for KnowledgeArticleVersion (ID={})'
            ).format(status, kav_id))

    def update_draft(self, kav_id, html):
        """Update the fields of an existing draft."""
        self.invalidate_cache()
        assert self.docset_scoped, "Need docset scoping to write safely"
        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        data = html.create_article_data()
        result = kav_api.update(kav_id, data)
        if result != HTTPStatus.NO_CONTENT:
            raise SalesforceError((
                'Error updating draft KnowledgeArticleVersion (ID={})'
            ).format(kav_id))
        return result

    @property
    def docset_scoped(self):
        return self.docset_uuid != self.ALL_DOCSETS

    def set_docset_index(self, local_docset_obj):
        sf_docset_api = getattr(self.api, settings.SALESFORCE_DOCSET_SOBJECT)
        sf_docset_id = self.sf_docset["Id"]

        if not local_docset_obj.index_article_ka_id:
            url_name = local_docset_obj.index_article_url
            assert url_name
            kav = [a for a in self.article_info_cache("Online") if a["UrlName"] == url_name][0]
            ka_id = kav["KnowledgeArticleId"]
            data = {settings.SALESFORCE_DOCSET_INDEX_REFERENCE_FIELD: ka_id}
            sf_docset_api.update(sf_docset_id, data)
            local_docset_obj.index_article_ka_id = ka_id
            local_docset_obj.save()
