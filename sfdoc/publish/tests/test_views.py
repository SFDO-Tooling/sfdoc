import json

from django.test import RequestFactory
from test_plus.test import TestCase

from ..models import EasyditaBundle
from .. import views


class BaseViewTestCase(TestCase):

    def setUp(self):
        self.user = self.make_user()
        self.factory = RequestFactory()


class TestWebhookView(BaseViewTestCase):

    def test_post_webhook(self):
        request = self.factory.post(
            '/publish/webhook/',
            data=json.dumps({'resource_id': 1}),
            content_type='application/json',
        )
        request.user = self.user
        response = views.webhook(request)
        self.response_200(response)
        self.assertEqual(EasyditaBundle.objects.count(), 1)
