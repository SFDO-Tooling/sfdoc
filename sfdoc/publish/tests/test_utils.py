import os
from tempfile import TemporaryDirectory
from django.test import override_settings
from test_plus.test import TestCase
from django.conf import settings

from ..utils import is_url_whitelisted, find_bundle_root_directory, s3_key_to_relative_pathname, bundle_relative_path
from .. import utils

class TestIsUrlWhitelisted(TestCase):

    @override_settings(WHITELIST_URL=['http://www.example.com'])
    def test_url_whitelist_exact(self):
        self.assertTrue(is_url_whitelisted('http://www.example.com'))
        self.assertTrue(is_url_whitelisted("foo"))
        self.assertFalse(is_url_whitelisted("http://youtube.com"))
    
    @override_settings(WHITELIST_URL=['*.example.com/*'])
    def test_url_whitelist_wildcard(self):
        self.assertTrue(is_url_whitelisted('http://www.example.com/a'))
        self.assertTrue(is_url_whitelisted("foo"))
        self.assertFalse(is_url_whitelisted("http://youtube.com"))

class TestFindRootDirectory(TestCase):
    def test_find_root_directory_simple(self):
        with TemporaryDirectory() as td:

            # Test Up towards /
            jazzy = td+"/foo/bar/baz/jaz"
            os.makedirs(jazzy, exist_ok=True)
            with open(td+"/foo/bar/log.txt", "w") as w:
                # could be any string
                w.write("https://www.youtube.com/watch?v=upsZZ2s3xv8")
            bundle_root = find_bundle_root_directory(jazzy)
            self.assertEqual(bundle_root, td+"/foo/bar")

            # Test Down away from /
            deeper_root = td
            bundle_root = find_bundle_root_directory(deeper_root)
            self.assertEqual(bundle_root, td+"/foo/bar")

    def test_find_root_directory_failure(self):
        with TemporaryDirectory() as td:
            jazzy = td+"/foo/bar/baz/jaz"
            os.makedirs(jazzy, exist_ok=True)
            self.assertRaises(Exception, lambda: find_bundle_root_directory(jazzy))

    def test_bundle_relative_path(self):
        bundle_root = "/foo/bar/baz"
        path = "/foo/bar/baz/jazz/xyz.html"
        rc = bundle_relative_path(bundle_root, path)
        self.assertEqual(rc, "jazz/xyz.html")


class TestS3KeyToRelativePathname(TestCase):
    def test_s3_key_to_relative_pathname(self):
        pathname = "490/draft/foo/restore-apex-job.png"
        self.assertEqual(s3_key_to_relative_pathname(pathname), "foo/restore-apex-job.png")


class TestUnzip(TestCase):
    def test_basic_unzip(self):
        rootdir = os.path.abspath(os.path.join(__file__, "../../../.."))
        tempdir = TemporaryDirectory()
        utils.unzip(os.path.join(rootdir, "testdata/matryoshka.zip"), tempdir.name)
        self.assertTrue(os.path.exists(tempdir.name + "/foo/bar/foo.zip"))
        self.assertTrue(os.path.exists(tempdir.name + "/foo/bar/foobar.txt"))
        self.assertFalse(os.path.exists(tempdir.name + "/foo/bar/foo"))
        self.assertFalse(os.path.exists(tempdir.name + "/foo/bar/foo/bar/foobar.txt"))

    def test_recursive_unzip(self):
        rootdir = os.path.abspath(os.path.join(__file__, "../../../.."))
        with TemporaryDirectory() as tempdir:
            utils.unzip(os.path.join(rootdir, "testdata/matryoshka.zip"), tempdir, recursive=True)
            self.assertTrue(os.path.exists(tempdir + "/foo/bar/foo.zip"))
            self.assertTrue(os.path.exists(tempdir + "/foo/bar/foobar.txt"))
            self.assertTrue(os.path.exists(tempdir + "/foo/bar/foo"))
            self.assertTrue(os.path.exists(tempdir + "/foo/bar/foo/foo/bar/foobar.txt"))


class MiscUtilTets(TestCase):
    @override_settings(SKIP_HTML_FILES=['index.html'])
    def test_article_link_limit_over(self):
        self.assertTrue(utils.skip_html_file('index.html'))
        self.assertFalse(utils.skip_html_file('foo/index.html'))
        self.assertFalse(utils.skip_html_file('index'))

    def test_is_html(self):
        self.assertTrue(utils.is_html("foo.htm"))
        self.assertTrue(utils.is_html("/abc/foo.htm"))
        self.assertTrue(utils.is_html("/abc/foo.html"))
        self.assertFalse(utils.is_html("foo.htmla"))
        self.assertFalse(utils.is_html("foo.ht"))
