from urllib.parse import urljoin

from django.conf import settings
import responses
from test_plus.test import TestCase

from ..salesforce import Salesforce


class TestSalesforce(TestCase):

    @responses.activate
    def test_init(self):
        """Get API to a Salesforce org."""
        url = urljoin(settings.SALESFORCE_LOGIN_URL, 'services/oauth2/token')
        json = {
            'instance_url': 'https://testinstance.salesforce.com',
            'access_token': 'abc123',
        }
        responses.add('POST', url=url, json=json)
        salesforce = Salesforce()
        self.assertEqual(len(responses.calls), 1)

    def test_get_community_loc_sandbox(self):
        instance_url = 'https://foundation--productdoc.cs70.my.salesforce.com'
        community_url = Salesforce.get_community_loc(
            'powerofus',
            instance_url,
            is_sandbox=True
            )

        self.assertEqual(community_url, 'productdoc-powerofus.cs70.force.com')

    def test_get_community_loc_prod(self):
        instance_url = 'https://foundation--productdoc.cs70.my.salesforce.com'
        community_url = Salesforce.get_community_loc(
            'powerofus',
            instance_url,
            is_sandbox=False
        )

        self.assertEqual(community_url, 'powerofus.force.com')

    @responses.activate
    def test_get_preview_url(self):
        url = urljoin(settings.SALESFORCE_LOGIN_URL, 'services/oauth2/token')
        json = {
            'instance_url': 'https://foundation--sb.cs70.my.salesforce.com',
            'access_token': 'abc123',
        }
        responses.add('POST', url=url, json=json)

        salesforce = Salesforce()
        salesforce.sandbox = True
        ka_url = salesforce.get_preview_url('123')

        self.assertEqual(
            ka_url,
            'https://sb-powerofus.cs70.force.com/knowledge/publishing/articlePreview.apexp?id=123'
        )
