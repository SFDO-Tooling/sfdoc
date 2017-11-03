import os
from tempfile import TemporaryDirectory

from django.conf import settings
import responses
from test_plus.test import TestCase

from ..models import Article
from ..models import EasyditaBundle
from .utils import gen_zip_file


class TestArticle(TestCase):

    def setUp(self):
        self.url_name = 'test-url-name'

    def test_get_url_name(self):
        html = '<html><head><meta name="UrlName" content="{}"></head></html>'.format(
            self.url_name,
        )
        url_name = Article.get_url_name(html)
        self.assertEqual(url_name, self.url_name)


class TestEasyditaBundle(TestCase):

    def setUp(self):
        self.easydita_bundle_id = 1
        self.easydita_bundle_url = '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.easydita_bundle_id,
        )

    @responses.activate
    def test_download(self):
        file_name = 'test.txt'
        file_contents = 'test file contents'
        responses.add(
            'GET',
            url=self.easydita_bundle_url,
            body=gen_zip_file(file_name, file_contents),
            content_type='application/zip',
        )
        easydita_bundle = EasyditaBundle(easydita_id=self.easydita_bundle_id)
        with TemporaryDirectory() as d:
            easydita_bundle.download(d)
            items = os.listdir(d)
            self.assertEqual(len(items), 1)
            name = items[0]
            self.assertEqual(name, file_name)
            with open(os.path.join(d, name)) as f:
                self.assertEqual(f.read(), file_contents)
        self.assertEqual(len(responses.calls), 1)
