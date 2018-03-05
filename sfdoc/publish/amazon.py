import filecmp
import os
from tempfile import TemporaryDirectory

import boto3
import botocore
from django.conf import settings

from .models import Image


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
            'Key': settings.AWS_S3_DRAFT_DIR + filename,
        }
        self.api.meta.client.copy_object(
            ACL='public-read',
            Bucket=settings.AWS_S3_BUCKET,
            CopySource=copy_source,
            Key=filename,
        )

    def delete(self, filename):
        """Delete an image from production location."""
        self.api.meta.client.delete_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=filename,
        )

    def ls(self):
        """List all objects in the bucket."""
        kwargs = {'Bucket': settings.AWS_S3_BUCKET}
        while True:
            response = self.api.meta.client.list_objects_v2(**kwargs)
            for item in response['Contents']:
                yield item
            if response['IsTruncated']:
                kwargs['ContinuationToken'] = response['NextContinuationToken']
            else:
                break

    def process_image(self, filename, bundle):
        """Upload image file to S3 if needed."""
        basename = os.path.basename(filename)
        key = settings.AWS_S3_DRAFT_DIR + basename
        with TemporaryDirectory() as tempdir:
            s3localname = os.path.join(tempdir, basename)
            try:
                # download image from root (production) dir for comparison
                self.api.meta.client.download_file(
                    settings.AWS_S3_BUCKET,
                    basename,
                    s3localname,
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # image does not exist on S3, create a new one
                    self.upload_image(filename, key)
                    Image.objects.create(
                        bundle=bundle,
                        filename=basename,
                        status=Image.STATUS_NEW,
                    )
                    return True
                else:
                    raise
            # image already in production; compare it to local image
            if filecmp.cmp(filename, s3localname):
                # files are the same, no update
                return False
            else:
                # files differ, update image
                self.upload_image(filename, key)
                Image.objects.create(
                    bundle=bundle,
                    filename=basename,
                    status=Image.STATUS_CHANGED,
                )
                return True

    def upload_image(self, filename, key):
        with open(filename, 'rb') as f:
            self.api.meta.client.put_object(
                ACL='public-read',
                Body=f,
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
            )
