import filecmp
import os
from tempfile import TemporaryDirectory

import boto3
import botocore
from django.conf import settings

from .models import Image


class S3:

    def __init__(self, draft):
        self.api = boto3.resource('s3')
        self.draft = bool(draft)

    def copy_to_production(self, filename):
        """
        Copy image from draft to production on S3.
        Production images are located in the root of the bucket.
        Draft images are located in a directory specified by environment
        variable AWS_STORAGE_BUCKET_NAME.
        """
        copy_source = {
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': settings.S3_IMAGES_DRAFT_DIR + filename,
        }
        self.api.meta.client.copy(
            copy_source,
            settings.AWS_STORAGE_BUCKET_NAME,
            filename,
        )

    def process_image(self, filename, easydita_bundle):
        """Upload image file to S3 if needed."""
        basename = os.path.basename(filename)
        key = basename
        if self.draft:
            key = settings.S3_IMAGES_DRAFT_DIR + key
        s3localname = os.path.join(d, basename)
        with TemporaryDirectory() as d:
            try:
                # download image by name
                self.api.meta.client.download_file(
                    settings.AWS_STORAGE_BUCKET_NAME,
                    key,
                    s3localname,
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # image does not exist on S3, create a new one
                    upload_image(filename, key)
                    Image.objects.create(
                        easydita_bundle=easydita_bundle,
                        filename=basename,
                    )
                else:
                    raise
            # image exists on S3 already, compare it to local image
            if not filecmp.cmp(filename, s3localname):
                # files differ, update image
                upload_image(filename, key)
                Image.objects.create(
                    easydita_bundle=easydita_bundle,
                    filename=basename,
                )

    def upload_image(self, filename, key):
        with open(filename, 'rb') as f:
            self.api.meta.client.put_object(
                ACL='public-read',
                Body=f,
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=key,
            )
