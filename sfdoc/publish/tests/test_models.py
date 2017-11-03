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
        html_str = (
            '<html>'
            '<head>'
            '<meta name="Title" content="{}">'
            '<meta name="UrlName" content="{}">'
            '</head>'
            '<body>'
            '<div class="row-fluid">{}</div>'
            '</body>'
            '</html>'
        )
        self.body = 'Example article content'
        self.title = 'Test Title'
        self.url_name = 'test-url-name'
        self.html = html_str.format(self.title, self.url_name, self.body)

    def test_get_url_name(self):
        url_name = Article.get_url_name(self.html)
        self.assertEqual(url_name, self.url_name)

    def test_parse(self):
        article = Article(html=self.html)
        article.parse()
        self.assertEqual(article.body, self.body)
        self.assertEqual(article.title, self.title)
        self.assertEqual(article.url_name, self.url_name)

    def test_scrub(self):
        article = Article(body=self.body)
        article.scrub()
        self.assertEqual(article.body, self.body + '\n')


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
