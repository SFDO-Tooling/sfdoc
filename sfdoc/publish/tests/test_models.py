import os
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup
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
            '<body>{}</body>'
            '</html>'
        )
        body_str = (
            '<div class="row-fluid">'
            '<img src="{}/test-image.png">'
            '<p>Example article content</p>'
            '</div>'
        )
        self.body = body_str.format(settings.IMAGES_URL_PLACEHOLDER)
        self.title = 'Test Title'
        self.url_name = 'test-url-name'
        self.html = html_str.format(self.title, self.url_name, self.body)

    def test_get_url_name(self):
        url_name = Article.get_url_name(self.html)
        self.assertEqual(url_name, self.url_name)

    def test_parse(self):
        article = Article(html_new=self.html)
        article.parse()
        soup = BeautifulSoup(self.body, 'html.parser')
        self.assertEqual(article.body_new, soup.prettify())
        self.assertEqual(article.title_new, self.title)

    def test_scrub(self):
        Article.scrub(self.html)

    def test_update_image_links(self):
        article = Article(body_new=self.body)
        article.update_image_links()
        self.assertIn(settings.IMAGES_URL_ROOT, article.body_new)
        self.assertNotIn(settings.IMAGES_URL_PLACEHOLDER, article.body_new)


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
