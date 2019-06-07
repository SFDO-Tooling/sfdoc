import filecmp
import os
from tempfile import TemporaryDirectory

import boto3
import botocore
from django.conf import settings

from .models import Image
from . import utils


class S3:

    def __init__(self):
        self.api = boto3.resource('s3')

    def copy_to_production(self, filename):
        """
        Copy image from draft to production on S3.
        Production images are located in the root of the bucket.
        Draft images are located in a directory specified by environment
        variable AWS_S3_BUCKET.
        """
        copy_source = {
            'Bucket': settings.AWS_S3_BUCKET,
            'Key': settings.AWS_S3_DRAFT_IMG_DIR + filename,
        }
        self.api.meta.client.copy_object(
            ACL='public-read',
            Bucket=settings.AWS_S3_BUCKET,
            CopySource=copy_source,
            Key=settings.AWS_S3_PUBLIC_IMG_DIR + filename,
        )

    def delete(self, filename):
        """Delete an image from production location."""
        self.api.meta.client.delete_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=filename,
        )

    def delete_draft_images(self):
        """Delete all draft images at once."""
        objects = []
        for item in self.iter_objects(prefix=settings.AWS_S3_DRAFT_IMG_DIR):
            objects.append({'Key': item['Key']})
        if objects:
            self.api.meta.client.delete_objects(
                Bucket=settings.AWS_S3_BUCKET,
                Delete={'Objects': objects},
            )

    def iter_objects(self, prefix=None):
        """Iterate over all objects in the bucket."""
        kwargs = {'Bucket': settings.AWS_S3_BUCKET}
        if prefix:
            kwargs['Prefix'] = prefix
        while True:
            response = self.api.meta.client.list_objects_v2(**kwargs)
            if 'Contents' not in response:
                break
            for item in response['Contents']:
                yield item
            if response['IsTruncated']:
                kwargs['ContinuationToken'] = response['NextContinuationToken']
            else:
                break

    def process_image(self, filename, bundle, rootpath):
        """Upload image file to S3 if needed."""
        relative_filename = utils.bundle_relative_path(rootpath, filename)
        key = settings.AWS_S3_DRAFT_IMG_DIR + relative_filename
        with TemporaryDirectory() as tempdir:
            s3localname = os.path.join(tempdir, relative_filename)
            os.makedirs(os.path.dirname(s3localname))
            try:
                # download image from root (production) dir for comparison
                self.api.meta.client.download_file(
                    settings.AWS_S3_BUCKET,
                    key,
                    s3localname,
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # image does not exist on S3, create a new one
                    self.upload_image(filename, key)

                    # And remember that we need to trasfer it to prod
                    Image.objects.create(
                        bundle=bundle,
                        filename=relative_filename,
                        status=Image.STATUS_NEW,
                    )
                    return
                else:
                    raise
            # image already in production; compare it to local image
            if filecmp.cmp(filename, s3localname):
                # files are the same, no update
                return
            else:
                # files differ, update image
                self.upload_image(filename, key)
                Image.objects.create(
                    bundle=bundle,
                    filename=relative_filename,
                    status=Image.STATUS_CHANGED,
                )
                return

    def upload_image(self, filename, key):
        with open(filename, 'rb') as f:
            self.api.meta.client.put_object(
                ACL='public-read',
                Body=f,
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
            )
