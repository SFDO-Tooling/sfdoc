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


def skip_html_file(filename):
    for skip_item in settings.SKIP_HTML_FILES:
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


def find_bundle_root_directory(origpath):
    matchfile = "log.txt"
    path = origpath

    # look up from origpath toward /
    while len(path) > 1:
        if os.path.exists(os.path.join(path, "log.txt")):
            return path
        oldpath = path
        path = os.path.dirname(oldpath)
        assert len(oldpath) > len(path), f"{oldpath} <= {path}"

    # look down from origpath away from /
    for root, dirs, files in os.walk(origpath):
        if matchfile in files:
            return root

    raise FileNotFoundError("Cannot find log.txt to identify root directory!")


def s3_key_to_relative_pathname(key):
    build_id, branch, path = key.split("/", 2)
    assert int(build_id) + 1
    assert branch in ("draft", "release")
    return path


def bundle_relative_path(bundle_root, path):
    assert os.path.isabs(path)
    return os.path.relpath(path, bundle_root)
