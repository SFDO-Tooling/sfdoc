from calendar import timegm
from datetime import datetime
from http import HTTPStatus
from urllib.parse import urljoin

from django.conf import settings
import jwt
import requests
from simple_salesforce import Salesforce as SimpleSalesforce

from .exceptions import SalesforceError
from .html import parse_html
from .html import replace_image_links


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
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
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

    def create_article(self, url_name, title, summary, body):
        """Create a new article in draft state."""
        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        data = {
            'UrlName': url_name,
            'Title': title,
            'Summary': summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: body,
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
            msg = (
                'Error publishing KnowledgeArticleVersion (ID={})'
            ).format(kav_id)
            raise SalesforceError(msg)
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

    def update_draft(self, kav_id, title, summary, body):
        """Update the fields of an existing draft."""
        kav_api = getattr(self.api, settings.SALESFORCE_ARTICLE_TYPE)
        data = {
            'Title': title,
            'Summary': summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: body,
        }
        result = kav_api.update(kav_id, data)
        if result != HTTPStatus.NO_CONTENT:
            msg = (
                'Error updating draft KnowledgeArticleVersion (ID={})'
            ).format(kav_id)
            raise KnowlegeError(msg)
        return result

    def upload_draft(self, html):
        """Create a draft KnowledgeArticleVersion."""

        # parse article fields from HTML
        url_name, title, summary, body = parse_html(html)

        # update image links to use Amazon S3
        body = replace_image_links(body)

        # search for existing draft. if found, update fields and return
        result = self.query_articles(url_name, 'draft')
        if result['totalSize'] == 1:  # cannot be > 1
            kav_id = result['records'][0]['id']
            self.update_draft(kav_id, title, summary, body)
            return kav_id, url_name, title

        # no drafts found. search for published article
        result = self.query_articles(url_name, 'online')
        if result['totalSize'] == 0:
            # new article
            kav_id = self.create_article(url_name, title, summary, body)
        elif result['totalSize'] == 1:
            # new draft of existing article
            record = result['records'][0]

            # check for changes in article fields
            if (
                title == record['Title'] and
                summary == record['Summary'] and
                body == record[settings.SALESFORCE_ARTICLE_BODY_FIELD]
            ):
                # no update
                return None, url_name, title

            # create draft copy of published article
            url = (
                self.api.base_url +
                'knowledgeManagement/articleVersions/masterVersions'
            )
            data = {'articleId': record['KnowledgeArticleId']}
            result = self.api._call_salesforce('POST', url, json=data)
            if result.status_code != HTTPStatus.CREATED:
                msg = (
                    'Error creating new draft for KnowlegeArticle (ID={})'
                ).format(record['KnowledgeArticleId'])
                raise KnowlegeError(msg)
            kav_id = result.json()['id']
            self.update_draft(kav_id, title, summary, body)

        return kav_id, url_name, title
