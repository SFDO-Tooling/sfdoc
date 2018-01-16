from django.conf import settings
import responses
from test_plus.test import TestCase

from ..salesforce import get_salesforce_api
from .utils import mock_salesforce_auth


class TestGetSalesforceApi(TestCase):

    def setUp(self):
        self.instance_url = 'https://testinstance.salesforce.com'

    @responses.activate
    def test_get_salesforce_api(self):
        """Get API to a Salesforce org."""
        mock_salesforce_auth(self.instance_url)
        sfapi = get_salesforce_api()
        self.assertEqual(len(responses.calls), 1)
