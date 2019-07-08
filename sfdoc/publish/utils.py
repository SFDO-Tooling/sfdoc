import fnmatch
import os
import logging
import subprocess
from urllib.parse import urlparse
from zipfile import ZipFile

from django.conf import settings


def is_html(filename):
    name, ext = os.path.splitext(filename)
    if ext.lower() in (".htm", ".html"):
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


def _filternames(open_zipfile, ignore_patterns):
    """Generate a list of files to extract from a zipfile which do not match a pattern"""
    if ignore_patterns:
        namelist = set(open_zipfile.namelist())
        for pattern in ignore_patterns:
            namelist -= set(fnmatch.filter(namelist, pattern))
        return list(namelist)


# TODO: tests for the ignore_patterns feature
def unzip(zipfile, path, recursive=False, ignore_patterns=None):
    """Recursive unzip. EasyDITA bundles consist of double-zipped zipfiles."""
    with ZipFile(zipfile) as f:
        names = _filternames(f, ignore_patterns)
        f.extractall(path, names)
    if recursive:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                root, ext = os.path.splitext(filename)
                if ext.lower() == ".zip":
                    unzip(
                        os.path.join(dirpath, filename),
                        os.path.join(dirpath, root),
                        recursive,
                        ignore_patterns
                    )


def find_bundle_root_directory(origpath):
    """Find the root directory for a bundle by looking for log.txt in parent and child directories"""
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


def bundle_relative_path(bundle_root, path):
    """Remove the bundle part of the path"""
    assert os.path.isabs(path)
    return os.path.relpath(path, bundle_root)


logger = logging.getLogger("commands")


def run_command(*args, **kwargs):
    logger.info(" ".join(args))
    try:
        return subprocess.run(args, **kwargs, check=True, text=True)
    except Exception as e:
        logger.error("Subprocess problem! {}", repr(e))
        print("Subprocess problem!", repr(e))
        raise e


def s3_sync(source, target, delete=False):
    """Sync directory to S3 or S3 to directory"""
    args = ["aws", "s3", "sync", source, target]
    
    if delete:
        args.append("--delete")
    run_command(*args)


def sync_directories(source, target):
    """Keep two directories in sync"""
    if not source.endswith("/"):
        source += "/"
    run_command("rsync", "-r", source, target)
