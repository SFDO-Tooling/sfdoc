import os
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup
from django.conf import settings
import responses
from test_plus.test import TestCase

from ..models import Article
from ..models import EasyditaBundle
from ..models import Image
from ..models import Webhook

from . import utils


class TestArticle(TestCase):

    def setUp(self):
        self.article = self.create_article()

    def create_article(self):
        easydita_bundle = EasyditaBundle.objects.create(
            easydita_id='0123456789',
            easydita_resource_id='9876543210',
        )
        ka_id = 'kA0123456789012345'
        draft_preview_url = (
            'https://test1.salesforce.com/knowledge/publishing/'
            'articlePreview.apexp?id={}'
        ).format(ka_id[:15])  # reduce to 15 char ID
        return Article.objects.create(
            draft_preview_url=draft_preview_url,
            easydita_bundle=easydita_bundle,
            ka_id=ka_id,
            kav_id='ka9876543210987654',
            title='Test Article',
            url_name='Test-Article',
        )

    def test_article_str(self):
        self.assertEqual(
            str(self.article),
            'Article {}: {}'.format(self.article.pk, self.article.title),
        )


class TestEasyditaBundle(TestCase):

    def setUp(self):
        self.easydita_bundle_id = 1
        self.easydita_bundle_url = '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.easydita_bundle_id,
        )
        self.articles = [utils.gen_article(n) for n in range(1, 3)]

    @responses.activate
    def test_download(self):
        easydita_bundle = EasyditaBundle.objects.create(
            easydita_id=self.easydita_bundle_id,
        )
        utils.mock_easydita_bundle_download(
            easydita_bundle.url,
            self.articles,
        )
        with TemporaryDirectory() as d:
            easydita_bundle.download(d)
            items = sorted(os.listdir(d))
            self.assertEqual(len(items), len(self.articles))
            for article, item in zip(self.articles, items):
                self.assertEqual(item, article['filename'])
                content = utils.create_test_html(
                    article['url_name'],
                    article['title'],
                    article['summary'],
                    article['body'],
                )
                with open(os.path.join(d, item)) as f:
                    self.assertEqual(f.read(), content)
        self.assertEqual(len(responses.calls), 1)


class TestImage(TestCase):

    def setUp(self):
        self.image = self.create_image()

    def create_image(self):
        easydita_bundle = EasyditaBundle.objects.create(
            easydita_id='0123456789',
            easydita_resource_id='9876543210',
        )
        return Image.objects.create(
            easydita_bundle=easydita_bundle,
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
        easydita_bundle = EasyditaBundle.objects.create(
            easydita_id='0123456789',
            easydita_resource_id='9876543210',
        )
        return Webhook.objects.create(
            body=r'{}',
            easydita_bundle=easydita_bundle,
        )

    def test_webhook_str(self):
        self.assertEqual(
            str(self.webhook),
            'Webhook {}'.format(self.webhook.pk),
        )
