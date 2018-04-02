from test_plus.test import TestCase
from django.test import override_settings

from ..html import HTML

from . import utils


class TestHTML(TestCase):

    def setUp(self):
        self.article = utils.gen_article(1)
        self.html_s = utils.create_test_html(
            self.article['url_name'],
            self.article['title'],
            self.article['summary'],
            self.article['body'],
        )

    def test_init(self):
        html = HTML(self.html_s)
        self.assertEqual(html.url_name, self.article['url_name'])
        self.assertEqual(html.title, self.article['title'])
        self.assertEqual(html.summary, self.article['summary'])
        self.assertEqual(html.body, self.article['body'])

    @override_settings(SALESFORCE_ARTICLE_URL_PATH_PREFIX='/articles/')
    def test_article_href_update(self):
        source = utils.create_test_html(
            'test-article',
            'Test Article Title',
            'This is a test summary',
            '<a href="Product_Docs/V4S/topics/Test-Path.html">test</a>\n'
            '<a href="Product_Docs/V4S/topics/Test-Path2.html#foo">test</a>\n',
        )
        html = HTML(source)

        html.update_links_draft()

        self.assertIn('href="/articles/Test-Path"', html.body)
        self.assertNotIn('Product_Docs/V4S/topics/Test-Path.html', html.body)

        self.assertIn('href="/articles/Test-Path2#foo"', html.body)
        self.assertNotIn('Product_Docs/V4S/topics/Test-Path2.html', html.body)
