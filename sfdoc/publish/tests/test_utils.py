from django.test import override_settings
from test_plus.test import TestCase

from ..utils import is_url_whitelisted


class TestIsUrlWhitelisted(TestCase):

    @override_settings(URL_WHITELIST=['http://www.example.com'])
    def test_url_whitelist_exact(self):
        self.assertTrue(is_url_whitelisted('http://www.example.com'))
    
    @override_settings(URL_WHITELIST=['*.example.com/*'])
    def test_url_whitelist_wildcard(self):
        self.assertTrue(is_url_whitelisted('http://www.example.com/a'))
