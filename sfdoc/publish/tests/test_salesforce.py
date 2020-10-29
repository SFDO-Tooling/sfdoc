from urllib.parse import urljoin

from unittest import skip, mock
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.test import override_settings
import responses
from test_plus.test import TestCase
import pytest

from ..salesforce import SalesforceArticles, sf_api_logger, get_community_base_url
from .utils import create_test_html
from simple_salesforce import exceptions as SimpleSalesforceExceptions


from sfdoc.publish.html import HTML
from sfdoc.publish.models import Article, Bundle


def get_salesforce_instance(instance_url, sandbox):
    """Get an instance of the Salesforce object."""
    url = urljoin(settings.SALESFORCE_LOGIN_URL, "services/oauth2/token")
    if sandbox:
        url = url.replace("login", "test")
    json = {
        "instance_url": instance_url,
        "access_token": "abc123",
    }
    responses.add("POST", url=url, json=json)
    SalesforceArticles.api = None
    return SalesforceArticles("pretend_UUID")


class TestSalesforceArticles(TestCase):
    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=True)
    def test_init_sandbox(self):
        """Get API to a Salesforce sandbox org."""
        SalesforceArticles.api = None  # clear connection cache
        get_salesforce_instance(
            "https://testinstance.salesforce.com",
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=False)
    def test_init_prod(self):
        """Get API to a Salesforce production org."""
        SalesforceArticles.api = None  # clear connection cache
        get_salesforce_instance(
            "https://testinstance.salesforce.com",
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=False)
    def test_exception_handling(self):
        SalesforceArticles.api = None  # clear connection cache
        salesforce_instance = get_salesforce_instance(
            "https://testinstance.salesforce.com",
            settings.SALESFORCE_SANDBOX,
        )
        with TemporaryDirectory() as t:
            html_file = Path(t) / "temp.html"
            markup = create_test_html("TheUrlName", "bar", "baz", "jazz")
            html_file.write_text(markup)
            html = HTML(str(html_file), t)
        bundle = Bundle()
        bundle.easydita_resource_id = "OldDocsetId"
        bundle.save()
        Article.objects.create(
            bundle=bundle,
            kav_id="kav_id",
            status=Article.STATUS_DELETED,
            title="Title",
            url_name="TheUrlName",
        )
        with mock.patch.object(
            type(salesforce_instance), "sf_docset", {"Id": "FakeUUID"}
        ), mock.patch.object(
            salesforce_instance.api, settings.SALESFORCE_ARTICLE_TYPE
        ) as kav_api, mock.patch.object(
            sf_api_logger, "error"
        ) as error_logger:
            kav_api.create.side_effect = (
                SimpleSalesforceExceptions.SalesforceMalformedRequest("", "", "", "")
            )
            with pytest.raises(SimpleSalesforceExceptions.SalesforceMalformedRequest):
                salesforce_instance.create_article(html)
            assert "TheUrlName" in error_logger.mock_calls[0][1][0]
            assert (
                "Perhaps the article moved between docsets?"
                in error_logger.mock_calls[1][1][0]
            )
            assert "OldDocsetId" in error_logger.mock_calls[2][1][0]
            assert "FakeUUID" in error_logger.mock_calls[3][1][0]


class TestCommunityUrl(TestCase):
    @responses.activate
    @override_settings(SALESFORCE_SANDBOX=True)
    def test_get_community_loc_sandbox(self):
        # determining sandbox URL *requires* auth to SFDC
        salesforce = get_salesforce_instance(
            "https://foundation--productdoc.cs70.my.salesforce.com",
            settings.SALESFORCE_SANDBOX,
        )
        self.assertEqual(
            salesforce.get_base_url(),
            "https://productdoc-{}.cs70.force.com".format(
                settings.SALESFORCE_COMMUNITY
            ),
        )

    @override_settings(SALESFORCE_SANDBOX=False)
    def test_get_community_loc_prod(self):
        # determining non-sandbox URL does not require request to SFDC
        self.assertEqual(
            get_community_base_url(),
            "https://{}.force.com".format(settings.SALESFORCE_COMMUNITY),
        )
