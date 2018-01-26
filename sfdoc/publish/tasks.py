import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django_rq import job
from simple_salesforce.exceptions import SalesforceGeneralError

from .amazon import S3
from .exceptions import HtmlError
from .exceptions import SalesforceError
from .models import Article
from .models import EasyditaBundle
from .salesforce import Salesforce
from .utils import scrub_html


@job
def process_easydita_bundle(easydita_bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = easydita_bundle.STATUS_PROCESSING
    easydita_bundle.save()
    salesforce = Salesforce()
    with TemporaryDirectory() as d:
        easydita_bundle.download(d)

        # check all HTML files
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    filename_full = os.path.join(dirpath, filename)
                    with open(filename_full, 'r') as f:
                        html = f.read()
                    scrub_html(html)

        # upload article drafts and images
        s3 = S3(draft=True)
        publish_queue = []
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                filename_full = os.path.join(dirpath, filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    with open(filename_full, 'r') as f:
                        html = f.read()
                    kav_id = salesforce.upload_draft(html)
                    if kav_id:
                        Article.objects.create(
                            easydita_bundle=easydita_bundle,
                            kav_id=kav_id,
                        )
                elif ext.lower() in settings.IMAGE_EXTENSIONS:
                    result = s3.handle_image(filename_full)
                    if result in ('created', 'updated'):
                        Image.objects.create(
                            easydita_bundle=easydita_bundle,
                            filename=filename,
                        )

    msg = 'Processed easyDITA bundle {}'.format(easydita_bundle.easydita_id)
    easydita_bundle.status = easydita_bundle.STATUS_DRAFT
    easydita_bundle.save()
    return msg


@job
def publish_drafts(easydita_bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = easydita_bundle.STATUS_PUBLISHING
    easydita_bundle.save()
    salesforce = Salesforce()
    s3 = S3(draft=False)
    for article in easydita_bundle.articles:
        salesforce.publish_draft(kav_id)
    for image in easydita_bundle.images:
        s3.copy_to_production(image.filename)
    easydita_bundle.status = easydita_bundle.STATUS_PUBLISHED
    easydita_bundle.save()
    # process next bundle in queue
    qs = EasyditaBundle.objects.filter(status=easydita_bundle.STATUS_NEW)
    if qs:
        bundle = qs.earliest('time_last_received')
        process_easydita_bundle.delay(bundle.pk)
