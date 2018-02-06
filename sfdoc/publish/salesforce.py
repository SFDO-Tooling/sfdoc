from calendar import timegm
from datetime import datetime
from http import HTTPStatus
from urllib.parse import urljoin
from urllib.parse import urlparse

from django.conf import settings
import jwt
import requests
from simple_salesforce import Salesforce as SimpleSalesforce

from .exceptions import SalesforceError
from .html import HTML
from .models import Article


class Salesforce:
    """Interact with a Salesforce org."""

    def __init__(self):
        self.api = self._get_salesforce_api()

    def _get_salesforce_api(self):
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
        headers = {'Content-Type': 'application/html-www-form-urlencoded'}
        auth_url = urljoin(url, 'services/oauth2/token')
        response = requests.post(url=auth_url, data=data, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        sf = SimpleSalesforce(
            instance_url=response_data['instance_url'],
            session_id=response_data['access_token'],
            sandbox=settings.SALESFORCE_SANDBOX,
            version=settings.SALESFORCE_API_VERSION,
            client_id='sfdoc',
        )
        return sf

    def create_article(self, html):
        """Create a new article in draft state."""
        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        data = {
            'UrlName': html.url_name,
            'Title': html.title,
            'Summary': html.summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: html.body,
        }
        result = kav_api.create(data=data)
        kav_id = result['id']
        return kav_id

    def publish_draft(self, kav_id):
        """Publish a draft KnowledgeArticleVersion."""
        url = (
            self.api.base_url +
            'knowledgeManagement/articleVersions/masterVersions/{}'
        ).format(kav_id)
        data = {'publishStatus': 'online'}
        result = self.api._call_salesforce('PATCH', url, json=data)
        if result.status_code != HTTPStatus.NO_CONTENT:
            raise SalesforceError('Error publishing KnowledgeArticleVersion (ID={})'.format(kav_id))
        return result

    def query_articles(self, url_name, publish_status):
        """Query KnowledgeArticleVersion objects."""
        query_str = (
            "SELECT Id,KnowledgeArticleId,Title,Summary,{} FROM {} "
            "WHERE UrlName='{}' AND PublishStatus='{}' AND language='en_US'"
        ).format(
            settings.SALESFORCE_ARTICLE_BODY_FIELD,
            settings.SALESFORCE_ARTICLE_TYPE,
            url_name,
            publish_status,
        )
        result = self.api.query(query_str)
        return result

    def save_article(self, kav_id, html, easydita_bundle):
        o = urlparse(self.api.base_url)
        draft_preview_url = (
            '{}://{}/knowledge/publishing/'
            'articlePreview.apexp?id={}'
        ).format(o.scheme, o.netloc, kav_id)
        Article.objects.create(
            easydita_bundle=easydita_bundle,
            kav_id=kav_id,
            draft_preview_url=draft_preview_url,
            title=html.title,
            url_name=html.url_name,
        )

    def update_draft(self, kav_id, html):
        """Update the fields of an existing draft."""
        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        data = {
            'Title': html.title,
            'Summary': html.summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: html.body,
        }
        result = kav_api.update(kav_id, data)
        if result != HTTPStatus.NO_CONTENT:
            raise KnowlegeError('Error updating draft KnowledgeArticleVersion (ID={})'.format(kav_id))
        return result

    def process_article(self, html_raw, easydita_bundle):
        """Create a draft KnowledgeArticleVersion."""

        # init HTML utility class
        html = HTML(html_raw)

        # update image links to use Amazon S3
        html.update_image_links()

        # search for existing draft. if found, update fields and return
        result = self.query_articles(html.url_name, 'draft')
        if result['totalSize'] == 1:  # cannot be > 1
            kav_id = result['records'][0]['id']
            self.update_draft(kav_id, html)
            self.save_article(kav_id, html, easydita_bundle)
            return

        # no drafts found. search for published article
        result = self.query_articles(html.url_name, 'online')
        if result['totalSize'] == 0:
            # new article
            kav_id = self.create_article(html)
        elif result['totalSize'] == 1:
            # new draft of existing article
            record = result['records'][0]

            # check for changes in article fields
            if (
                html.title == record['Title'] and
                html.summary == record['Summary'] and
                html.body == record[settings.SALESFORCE_ARTICLE_BODY_FIELD]
            ):
                # no update
                return

            # create draft copy of published article
            url = (
                self.api.base_url +
                'knowledgeManagement/articleVersions/masterVersions'
            )
            data = {'articleId': record['KnowledgeArticleId']}
            result = self.api._call_salesforce('POST', url, json=data)
            if result.status_code != HTTPStatus.CREATED:
                raise KnowlegeError('Error creating new draft for KnowlegeArticle (ID={})'.format(record['KnowledgeArticleId']))
            kav_id = result.json()['id']
            self.update_draft(kav_id, html)

        self.save_article(kav_id, html, easydita_bundle)
