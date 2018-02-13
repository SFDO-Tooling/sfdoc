import fnmatch
import os
from urllib.parse import urlparse
from zipfile import ZipFile

from django.conf import settings


def is_url_whitelisted(url):
    """Determine if a URL is whitelisted."""
    if not urlparse(url).scheme:
        # not an external link, implicitly whitelisted
        return True
    for wl_item in settings.URL_WHITELIST:
        if fnmatch.fnmatch(url, wl_item):
            return True
    return False


def unzip(zipfile, path, recursive=False):
    """Recursive unzip."""
    print('ZIP file: {}'.format(zipfile))
    print('Path: {}'.format(path))
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
