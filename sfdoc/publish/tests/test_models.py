import os
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup
from django.conf import settings
import responses
from test_plus.test import TestCase

from ..models import EasyditaBundle
from .utils import create_test_html
from .utils import gen_article
from .utils import mock_easydita_bundle_download


class TestEasyditaBundle(TestCase):

    def setUp(self):
        self.easydita_bundle_id = 1
        self.easydita_bundle_url = '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.easydita_bundle_id,
        )
        self.articles = [gen_article(n) for n in range(1, 3)]

    @responses.activate
    def test_download(self):
        easydita_bundle = EasyditaBundle.objects.create(
            easydita_id=self.easydita_bundle_id,
        )
        mock_easydita_bundle_download(
            easydita_bundle.url,
            self.articles,
        )
        with TemporaryDirectory() as d:
            easydita_bundle.download(d)
            items = os.listdir(d)
            self.assertEqual(len(items), len(self.articles))
            for article, item in zip(self.articles, items):
                self.assertEqual(item, article['filename'])
                content = create_test_html(
                    article['url_name'],
                    article['title'],
                    article['summary'],
                    article['body'],
                )
                with open(os.path.join(d, item)) as f:
                    self.assertEqual(f.read(), content)
        self.assertEqual(len(responses.calls), 1)
