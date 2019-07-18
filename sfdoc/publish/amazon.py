import filecmp
import os
from tempfile import TemporaryDirectory

import boto3
import botocore
from django.conf import settings

from .models import Image
from . import utils


class S3:

    def __init__(self, bundle):
        """
        Instantiate a scoped accessor for S3 appropriate to this bundle
        """
        self.api = boto3.resource('s3')
        self.bundle = bundle
        if bundle:
            self.docset_id = bundle.docset_id
        else:
            # There is one context where the class is created without bundle-scoping
            # and for now it is easier to do this than to make scoped and unscoped
            # classes...if only to keep the github PR easier to follow
            self.docset_id = None

    def copy_to_production(self, filename):
        """
        Copy image from draft to production on S3.
        """
        copy_source = {
            'Bucket': settings.AWS_S3_BUCKET,
            'Key': Image.get_storage_path(self.docset_id, filename, draft=True)
        }
        self.api.meta.client.copy_object(
            ACL='public-read',
            Bucket=settings.AWS_S3_BUCKET,
            CopySource=copy_source,
            Key=Image.get_storage_path(self.docset_id, filename, draft=False),
        )

    def delete(self, relfilename, draft):
        """Delete an image from production location."""
        key = Image.get_storage_path(self.docset_id, relfilename, draft)
        rc = self.api.meta.client.delete_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=key,
        )
        return rc

    def delete_draft_images(self):
        """Delete all draft images at once."""
        objects = []
        for item in self.iter_objects(prefix=Image.get_docset_s3_path(self.docset_id, draft=True)):
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

    def process_image(self, filename, rootpath):
        """Upload image file to S3 if needed."""
        relative_filename = utils.bundle_relative_path(rootpath, filename)
        draft_key = Image.get_storage_path(self.docset_id, relative_filename, draft=True)
        prod_key = Image.get_storage_path(self.docset_id, relative_filename, draft=False)
        with TemporaryDirectory(prefix=f"process_image_{os.path.basename(filename)}") as tempdir:
            s3localname = os.path.join(tempdir, relative_filename)
            os.makedirs(os.path.dirname(s3localname))
            try:
                # download image from root (production) dir for comparison
                self.api.meta.client.download_file(
                    settings.AWS_S3_BUCKET,
                    prod_key,
                    s3localname,
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # image does not exist on S3, create a new one
                    self.upload_image(filename, draft_key)

                    # Keep track of the fact that we need to transfer it to prod
                    Image.objects.create(
                        bundle=self.bundle,
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
                self.upload_image(filename, draft_key)
                Image.objects.create(
                    bundle=self.bundle,
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
