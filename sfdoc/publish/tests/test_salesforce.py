from urllib.parse import urljoin

from unittest import skip

from django.conf import settings
from django.test import override_settings
import responses
from test_plus.test import TestCase

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
    return SalesforceArticles("pretend_UUID")


class TestSalesforceArticles(TestCase):

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=True)
    def test_init_sandbox(self):
        """Get API to a Salesforce sandbox org."""
        get_salesforce_instance(
            'https://testinstance.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=False)
    def test_init_prod(self):
        """Get API to a Salesforce production org."""
        get_salesforce_instance(
            'https://testinstance.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=True)
    def test_get_community_loc_sandbox(self):

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

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=False)
    def test_get_community_loc_prod(self):
        salesforce = get_salesforce_instance(
            'https://foundation--productdoc.cs70.my.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(
            salesforce.get_base_url(),
            'https://{}.force.com'.format(
                settings.SALESFORCE_COMMUNITY
            )
        )

    @skip
    @override_settings(SALESFORCE_SANDBOX=True)
    @responses.activate
    def test_get_preview_url(self):
        salesforce = get_salesforce_instance(
            'https://foundation--sb.cs70.my.salesforce.com',
            settings.SALESFORCE_SANDBOX,
        )
        ka_url = salesforce.get_preview_url('123')
        self.assertEqual(
            ka_url,
            'https://sb-{}.cs70.force.com/knowledge/publishing/articlePreview.apexp?id=123'.format(
                settings.SALESFORCE_COMMUNITY
            ),
        )
