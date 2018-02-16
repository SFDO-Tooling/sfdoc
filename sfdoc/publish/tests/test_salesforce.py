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
