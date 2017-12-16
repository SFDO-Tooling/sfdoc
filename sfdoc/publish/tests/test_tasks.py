from django.conf import settings
import responses
from test_plus.test import TestCase

from ..models import EasyditaBundle
from ..tasks import process_easydita_bundle
from .utils import gen_article
from .utils import mock_create_article
from .utils import mock_create_draft
from .utils import mock_easydita_bundle_download
from .utils import mock_publish_draft
from .utils import mock_query
from .utils import mock_salesforce_auth
from .utils import mock_update_draft


class TestProcessEasyditaBundle(TestCase):

    def setUp(self):
        self.easydita_bundle_id = 1
        self.instance_url = 'https://testinstance.salesforce.com'
        self.articles = []
        for n in range(1, 3):
            self.articles.append(gen_article(n))

    @responses.activate
    def test_process_easydita_bundle(self):

        # download bundle from easyDITA
        easydita_bundle = EasyditaBundle.objects.create(
            easydita_id=self.easydita_bundle_id,
        )
        mock_easydita_bundle_download(
            easydita_bundle.url,
            self.articles,
        )

        # get Salesforce API
        mock_salesforce_auth(self.instance_url)

        # query for drafts matching URL name
        fields = [
            'Id',
            'KnowledgeArticleId',
            'Title',
            'Summary',
            settings.SALESFORCE_ARTICLE_BODY_FIELD,
        ]
        for a in self.articles:
            mock_query(
                self.instance_url,
                a['url_name'],
                'draft',
                fields=fields,
                return_val={'totalSize': 0},
            )

        # query for online (published) articles matching URL name
        # article 1, no hits
        mock_query(
            self.instance_url,
            self.articles[0]['url_name'],
            'online',
            fields=fields,
            return_val={'totalSize': 0},
        )

        # query for online (published) articles matching URL name
        # article 2, 1 hit
        mock_query(
            self.instance_url,
            self.articles[1]['url_name'],
            'online',
            fields=fields,
            return_val={
                'totalSize': 1,
                'records': [
                    {
                        'Id': (self.articles[1]['id']),
                        'KnowledgeArticleId': 1,
                        'Title': self.articles[1]['title'],
                        'Summary': self.articles[1]['summary'],
                        settings.SALESFORCE_ARTICLE_BODY_FIELD: 'foo',
                    }
                ],
            },
        )

        # create new ka & kav (article 1)
        mock_create_article(self.instance_url, self.articles[0]['id'])

        # create new draft for existing ka (article 2)
        mock_create_draft(self.instance_url, 1, self.articles[1]['id'])

        # update draft fields (article 2)
        mock_update_draft(self.instance_url, self.articles[1]['id'])

        # publish drafts
        for a in self.articles:
            mock_publish_draft(self.instance_url, a['id'])

        process_easydita_bundle(easydita_bundle.pk)

        self.assertEqual(len(responses.calls), 11)
