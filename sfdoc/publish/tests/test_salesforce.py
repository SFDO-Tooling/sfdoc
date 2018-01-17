from django.conf import settings
import responses
from test_plus.test import TestCase

from ..salesforce import Salesforce
from .utils import mock_salesforce_auth


class TestSalesforce(TestCase):

    def setUp(self):
        self.instance_url = 'https://testinstance.salesforce.com'

    @responses.activate
    def test__init__(self):
        """Get API to a Salesforce org."""
        mock_salesforce_auth(self.instance_url)
        salesforce = Salesforce()
        self.assertEqual(len(responses.calls), 1)
