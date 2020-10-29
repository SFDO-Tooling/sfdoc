import json

from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse
from test_plus.test import TestCase

from ..models import Article
from ..models import Bundle
from .. import views


class BaseViewTestCase(TestCase):
    def setUp(self):
        self.user = self.make_user()
        self.factory = RequestFactory()


class TestWebhookView(BaseViewTestCase):
    def test_post_webhook(self):
        request = self.factory.post(
            "/publish/webhook/",
            data=json.dumps({"resource_id": 1}),
            content_type="application/json",
        )
        request.user = self.user
        response = views.webhook(request)
        self.response_200(response)


class TestPublishView(BaseViewTestCase):
    def setUp(self):
        self.user = self.make_user("u")
        self.user.is_staff = True
        self.user.set_password("12345")
        self.user.save()
        self.client.login(username="u", password="12345")
        self.bundle = Bundle.objects.create(
            easydita_id="0123456789",
            easydita_resource_id="9876543210",
            status=Bundle.STATUS_DRAFT,
        )

    def create_article(self, status=Article.STATUS_NEW):
        return Article.objects.create(
            status=status,
            bundle=self.bundle,
            ka_id="kA123",
            kav_id="ka9876543210987654",
            title="Test Article",
            url_name="Test-Article",
        )

    def test_get_review_bundle(self):
        article = self.create_article()

        response = self.client.get(reverse("publish:review", args=(self.bundle.pk,)))

        self.assertEqual(response.status_code, 200)

        articles_new = response.context[0]["articles_new"]

        full_article_url = "https://{}.force.com{}?id={}{}".format(
            settings.SALESFORCE_COMMUNITY,
            settings.SALESFORCE_ARTICLE_PREVIEW_URL_PATH_PREFIX,
            article.ka_id,
            "&preview=true&pubstatus=d&channel=APP",
        )
        self.assertEqual(len(articles_new), 1)
        self.assertEqual(articles_new[0]["preview_url"], full_article_url)
