import json
import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django.utils.timezone import now
from django_rq import job

from .amazon import S3
from .html import scrub_html
from .models import EasyditaBundle
from .models import Webhook
from .salesforce import Salesforce


@job
def process_easydita_bundle(easydita_bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = EasyditaBundle.STATUS_PROCESSING
    easydita_bundle.time_processed = now()
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
                    salesforce.process_article(html, easydita_bundle)
                elif ext.lower() in settings.IMAGE_EXTENSIONS:
                    s3.process_image(filename_full, easydita_bundle)

    easydita_bundle.status = EasyditaBundle.STATUS_DRAFT
    easydita_bundle.save()
    return 'Processed easyDITA bundle (pk={})'.format(easydita_bundle.pk)


@job
def process_queue():
    """Process the next easyDITA bundle in the queue."""
    if EasyditaBundle.objects.filter(status__in=(
        EasyditaBundle.STATUS_PROCESSING,
        EasyditaBundle.STATUS_DRAFT,
        EasyditaBundle.STATUS_PUBLISHING,
    )):
        return 'Already processing an easyDITA bundle!'
    easydita_bundle = EasyditaBundle.objects.filter(
        status=EasyditaBundle.STATUS_QUEUED,
    ).earliest('time_queued')
    process_easydita_bundle.delay(easydita_bundle.pk)
    return 'Started processing next easyDITA bundle in queue (pk={})'.format(
        easydita_bundle.pk,
    )


@job
def process_webhook(pk):
    """Process an easyDITA webhook."""
    webhook = Webhook.objects.get(pk=pk)
    data = json.loads(webhook.body)
    easydita_id = data['resource_id']
    easydita_bundle, created = EasyditaBundle.objects.get_or_create(
        easydita_id=easydita_id,
    )
    webhook.easydita_bundle = easydita_bundle
    if created or easydita_bundle.is_complete():
        webhook.status = Webhook.STATUS_ACCEPTED
        easydita_bundle.status = EasyditaBundle.STATUS_QUEUED
        easydita_bundle.time_queued = now()
        easydita_bundle.save()
        if EasyditaBundle.objects.filter(
            status=EasyditaBundle.STATUS_QUEUED,
        ).count() == 1:
            # this is the only queued bundle
            process_queue.delay()
    else:
        webhook.status = Webhook.STATUS_REJECTED
    webhook.save()
    return 'Processed webhook (pk={})'.format(webhook.pk)


@job
def publish_drafts(easydita_bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHING
    easydita_bundle.save()
    salesforce = Salesforce()
    s3 = S3(draft=False)
    for article in easydita_bundle.articles:
        salesforce.publish_draft(kav_id)
    for image in easydita_bundle.images:
        s3.copy_to_production(image.filename)
    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHED
    easydita_bundle.save()
    process_queue.delay()
    return 'Published all drafts from easyDITA bundle (pk={})'.format(
        easydita_bundle.pk,
    )
