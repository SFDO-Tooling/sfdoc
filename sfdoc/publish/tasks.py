import json
import logging
from tempfile import TemporaryDirectory

from django.utils.timezone import now
from django_rq import job

from .amazon import S3
from .exceptions import SalesforceError
from .models import EasyditaBundle
from .models import Webhook
from .salesforce import Salesforce

logger = logging.getLogger(__name__)


@job('default', timeout=600)
def process_easydita_bundle(easydita_bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    logger.info('Processing easyDITA bundle {}'.format(easydita_bundle_pk))
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = EasyditaBundle.STATUS_PROCESSING
    easydita_bundle.time_processed = now()
    easydita_bundle.save()
    salesforce = Salesforce()
    s3 = S3(draft=True)
    with TemporaryDirectory() as tempdir:
        easydita_bundle.download(tempdir)
        easydita_bundle.process(tempdir, salesforce, s3)
    msg = 'Processed easyDITA bundle (pk={})'.format(easydita_bundle.pk)
    logger.info(msg)
    return msg


@job
def process_queue():
    """Process the next easyDITA bundle in the queue."""
    logger.info('Processing bundle queue')
    if EasyditaBundle.objects.filter(status__in=(
        EasyditaBundle.STATUS_PROCESSING,
        EasyditaBundle.STATUS_DRAFT,
        EasyditaBundle.STATUS_PUBLISHING,
    )):
        msg = 'Already processing an easyDITA bundle!'
        logger.info(msg)
        return msg
    easydita_bundle = EasyditaBundle.objects.filter(
        status=EasyditaBundle.STATUS_QUEUED,
    ).earliest('time_queued')
    process_easydita_bundle.delay(easydita_bundle.pk)
    msg = 'Started processing next easyDITA bundle in queue (pk={})'.format(
        easydita_bundle.pk,
    )
    logger.info(msg)
    return msg


@job
def process_webhook(pk):
    """Process an easyDITA webhook."""
    logger.info('Processing webhook {}'.format(pk))
    webhook = Webhook.objects.get(pk=pk)
    data = json.loads(webhook.body)
    if (
        data['event_id'] == 'dita-ot-publish-complete'
        and data['event_data']['publish-result'] == 'success'
    ):
        easydita_bundle, created = EasyditaBundle.objects.get_or_create(
            easydita_id=data['event_data']['output-uuid'],
            defaults={'easydita_resource_id': data['resource_id']},
        )
        webhook.easydita_bundle = easydita_bundle
        if created or easydita_bundle.is_complete():
            logger.info('Webhook accepted')
            webhook.status = Webhook.STATUS_ACCEPTED
            webhook.save()
            easydita_bundle.status = EasyditaBundle.STATUS_QUEUED
            easydita_bundle.time_queued = now()
            easydita_bundle.save()
            process_queue.delay()
        else:
            logger.info('Webhook rejected (already processing)')
            webhook.status = Webhook.STATUS_REJECTED
    else:
        logger.info('Webhook rejected (not dita-ot success)')
        webhook.status = Webhook.STATUS_REJECTED
    webhook.save()
    msg = 'Processed webhook (pk={})'.format(webhook.pk)
    logger.info(msg)
    return msg


@job('default', timeout=600)
def publish_drafts(easydita_bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    logger.info(
        'Publishing drafts for easyDITA bundle {}'.format(easydita_bundle_pk)
    )
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHING
    easydita_bundle.save()
    salesforce = Salesforce()
    s3 = S3(draft=False)
    for article in easydita_bundle.articles.all():
        try:
            salesforce.publish_draft(kav_id)
        except SalesforceError as e:
            easydita_bundle.set_error(e)
            raise
    for image in easydita_bundle.images.all():
        s3.copy_to_production(image.filename)
    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHED
    easydita_bundle.save()
    process_queue.delay()
    msg = 'Published all drafts from easyDITA bundle (pk={})'.format(
        easydita_bundle.pk,
    )
    logger.info(msg)
    return msg
