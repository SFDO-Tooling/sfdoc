from test_plus.test import TestCase
from django.test import override_settings

from ..html import HTML, collect_html_paths

from . import utils
import os
import logging

rootdir = os.path.abspath(os.path.join(__file__, "../../../.."))


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
        html = HTML(self.html_s, "", "")
        self.assertEqual(html.url_name, self.article['url_name'])
        self.assertEqual(html.title, self.article['title'])
        self.assertEqual(html.summary, self.article['summary'])
        self.assertEqual(html.body, self.article['body'])

    def generate_links(self, count):
        tpl = '<a href="Product_Docs/V4S/topics/{}.html">test</a>'
        return '\n'.join([tpl.format(i) for i in range(count)])

    @override_settings(SALESFORCE_ARTICLE_URL_PATH_PREFIX='/articles/')
    def test_article_href_update(self):
        source = utils.create_test_html(
            'test-article',
            'Test Article Title',
            'This is a test summary',
            '<a href="Product_Docs/V4S/topics/Test-Path.html">test</a>\n'
            '<a href="Product_Docs/V4S/topics/Test-Path2.html#foo">test</a>\n',
        )
        html = HTML(source, "/tmp/something/something/foo.html", "/tmp/something/")

        html.update_links_draft("some-uuid")

        self.assertIn('href="/articles/Test-Path"', html.body)
        self.assertNotIn('Product_Docs/V4S/topics/Test-Path.html', html.body)

        self.assertIn('href="/articles/Test-Path2#foo"', html.body)
        self.assertNotIn('Product_Docs/V4S/topics/Test-Path2.html', html.body)

    @override_settings(SALESFORCE_ARTICLE_LINK_LIMIT=10)
    def test_article_link_limit_under(self):
        source = utils.create_test_html(
            'test-article',
            'Test Article Title',
            'This is a test summary',
            self.generate_links(3),
        )
        html = HTML(source, "/tmp/something/something/foo.html", "/tmp/something/")
        html.update_links_draft('uuid', 'https://powerofus.force.com')

        self.assertNotIn('https://powerofus.force.com', html.body)

    @override_settings(SALESFORCE_ARTICLE_LINK_LIMIT=10)
    def test_article_link_limit_equal(self):
        source = utils.create_test_html(
            'test-article',
            'Test Article Title',
            'This is a test summary',
            self.generate_links(10),
        )

        html = HTML(source, "/tmp/something/something/foo.html", "/tmp/something/")

        html.update_links_draft('uuid', 'https://powerofus.force.com')

        self.assertNotIn('https://powerofus.force.com', html.body)

    @override_settings(SALESFORCE_ARTICLE_LINK_LIMIT=10)
    def test_article_link_limit_over(self):
        source = utils.create_test_html(
            'test-article',
            'Test Article Title',
            'This is a test summary',
            self.generate_links(11),
        )
        html = HTML(source, "/tmp/something/something/foo.html", "/tmp/something/")

        html.update_links_draft('uuid', 'https://powerofus.force.com')

        self.assertIn('https://powerofus.force.com', html.body)

    def test_collect_html(self):
        logger = logging.getLogger("test")
        testdita = os.path.join(rootdir, "testdata/sampledita")
        files = collect_html_paths(testdita, logger)
        files = [os.path.basename(file) for file in files]
        self.assertEqual(sorted(files), sorted(["fC-Documentation.html", "fC-Overview.html", "fC-Release-Notes.html", 
                                                "fC-FAQ.html", "fC-Guide.html"]))

    def test_update_links_production(self):
        html = """<body><a href="Product_Docs/V4S/topics/Test-Path2.html#foo">test</a>\n
                    <img src="https://dummydomain.s3.amazonaws.com/images/draft/some-uuid/path/img.png"></img>
                </body>
            """
        updated = HTML.update_links_production(html)
        assert "/draft/" not in updated
        assert "/public/" in updated
