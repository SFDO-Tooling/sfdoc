import os
from zipfile import ZipFile


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
