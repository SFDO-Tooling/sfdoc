import fnmatch
import os
from urllib.parse import urlparse
from zipfile import ZipFile

from django.conf import settings


def is_html(filename):
    name, ext = os.path.splitext(filename)
    if ext.lower() in ('.htm', '.html'):
        return True
    else:
        return False


def is_url_whitelisted(url):
    """Determine if a URL is whitelisted."""
    if not urlparse(url).scheme:
        # not an external link, implicitly whitelisted
        return True
    for wl_item in settings.WHITELIST_URL:
        if fnmatch.fnmatch(url, wl_item):
            return True
    return False


def skip_file(filename):
    for skip_item in settings.SKIP_FILES:
        if fnmatch.fnmatch(filename, skip_item):
            return True
    return False


def unzip(zipfile, path, recursive=False):
    """Recursive unzip."""
    with ZipFile(zipfile) as f:
        f.extractall(path)
    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                root, ext = os.path.splitext(filename)
                if ext.lower() == '.zip':
                    unzip(
                        os.path.join(dirpath, filename),
                        os.path.join(dirpath, root),
                        recursive,
                    )
