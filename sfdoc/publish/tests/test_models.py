from django.conf import settings
from test_plus.test import TestCase

from ..models import Article
from ..models import Bundle
from ..models import Image
from ..models import Webhook

from . import utils


class TestArticle(TestCase):

    def setUp(self):
        self.article = self.create_article()

    def create_article(self):
        bundle = Bundle.objects.create(
            easydita_id='0123456789',
            easydita_resource_id='9876543210',
        )
        return Article.objects.create(
            preview_url='',
            bundle=bundle,
            ka_id='kA0123456789012345',
            kav_id='ka9876543210987654',
            title='Test Article',
            url_name='Test-Article',
        )

    def test_article_str(self):
        s = str(self.article)
        self.assertIn(self.article.title, s)
        self.assertIn(self.article.url_name, s)


class TestBundle(TestCase):

    def setUp(self):
        self.bundle_id = 1
        self.bundle_url = '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.bundle_id,
        )
        self.docset_id = "some-uuid"
        self.articles = [utils.gen_article(n) for n in range(1, 3)]


class TestImage(TestCase):

    def setUp(self):
        self.image = self.create_image()

    def create_image(self):
        bundle = Bundle.objects.create(
            easydita_id='0123456789',
            easydita_resource_id='9876543210',
        )
        return Image.objects.create(
            bundle=bundle,
            filename='test.png',
        )

    def test_image_str(self):
        self.assertEqual(
            str(self.image),
            'Image {}: {}'.format(self.image.pk, self.image.filename),
        )


class TestWebhook(TestCase):

    def setUp(self):
        self.webhook = self.create_webhook()

    def create_webhook(self):
        bundle = Bundle.objects.create(
            easydita_id='0123456789',
            easydita_resource_id='9876543210',
        )
        return Webhook.objects.create(
            body=r'{}',
            bundle=bundle,
        )

    def test_webhook_str(self):
        self.assertEqual(
            str(self.webhook),
            'Webhook {}'.format(self.webhook.pk),
        )
