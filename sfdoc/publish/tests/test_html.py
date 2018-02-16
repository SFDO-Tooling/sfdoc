from test_plus.test import TestCase

from ..html import HTML
from ..html import get_links
from ..html import get_tags
from ..html import scrub_html
from ..html import update_image_links_production

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
