from urllib.parse import urljoin

from unittest import skip

from django.conf import settings
from django.test import override_settings
import responses
from test_plus.test import TestCase

from ..salesforce import get_community_base_url
from ..salesforce import SalesforceArticles


def get_salesforce_instance(instance_url, sandbox):
    """Get an instance of the Salesforce object."""
    url = urljoin(settings.SALESFORCE_LOGIN_URL, 'services/oauth2/token')
    if sandbox:
        url = url.replace('login', 'test')
    json = {
        'instance_url': instance_url,
        'access_token': 'abc123',
    }
    responses.add('POST', url=url, json=json)
    SalesforceArticles.api = None
    return SalesforceArticles("pretend_UUID")


class TestSalesforceArticles(TestCase):

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=True)
    def test_init_sandbox(self):
        """Get API to a Salesforce sandbox org."""
        SalesforceArticles.api = None  # clear connection cache
        get_salesforce_instance(
            'https://testinstance.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=False)
    def test_init_prod(self):
        """Get API to a Salesforce production org."""
        SalesforceArticles.api = None  # clear connection cache
        get_salesforce_instance(
            'https://testinstance.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(len(responses.calls), 1)


class TestCommunityUrl(TestCase):

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=True)
    def test_get_community_loc_sandbox(self):
        # determining sandbox URL *requires* auth to SFDC
        salesforce = get_salesforce_instance(
            'https://foundation--productdoc.cs70.my.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(
            salesforce.get_base_url(),
            'https://productdoc-{}.cs70.force.com'.format(
                settings.SALESFORCE_COMMUNITY
            )
        )

    @override_settings(SALESFORCE_SANDBOX=False)
    def test_get_community_loc_prod(self):
        # determining non-sandbox URL does not require request to SFDC
        self.assertEqual(
            get_community_base_url(),
            'https://{}.force.com'.format(
                settings.SALESFORCE_COMMUNITY
            )
        )
