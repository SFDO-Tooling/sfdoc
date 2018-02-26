import json
from tempfile import TemporaryDirectory

from django.utils.timezone import now
from django_rq import job

from .amazon import S3
from .exceptions import SalesforceError
from .logger import get_logger
from .models import Bundle
from .models import Webhook
from .salesforce import Salesforce


@job('default', timeout=600)
def process_bundle(bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    bundle = Bundle.objects.get(pk=bundle_pk)
    bundle.status = Bundle.STATUS_PROCESSING
    bundle.time_processed = now()
    bundle.save()
    logger = get_logger(bundle)
    logger.info('Processing easyDITA bundle {}'.format(bundle_pk))
    salesforce = Salesforce()
    s3 = S3()
    with TemporaryDirectory() as tempdir:
        bundle.download(tempdir)
        try:
            bundle.process(tempdir, salesforce, s3)
        except Exception as e:
            bundle.set_error(e)
            raise
    logger.info('Processed {}'.format(bundle))


@job
def process_queue():
    """Process the next easyDITA bundle in the queue."""
    if Bundle.objects.filter(status__in=(
        Bundle.STATUS_PROCESSING,
        Bundle.STATUS_DRAFT,
        Bundle.STATUS_PUBLISHING,
    )):
        return
    try:
        bundle = Bundle.objects.filter(
            status=Bundle.STATUS_QUEUED,
        ).earliest('time_queued')
    except Bundle.DoesNotExist as e:
        return
    process_bundle.delay(bundle.pk)


@job
def process_webhook(pk):
    """Process an easyDITA webhook."""
    webhook = Webhook.objects.get(pk=pk)
    logger = get_logger(webhook)
    logger.info('Processing webhook {}'.format(pk))
    data = json.loads(webhook.body)
    if (
        data['event_id'] == 'dita-ot-publish-complete'
        and data['event_data']['publish-result'] == 'success'
    ):
        bundle, created = Bundle.objects.get_or_create(
            easydita_id=data['event_data']['output-uuid'],
            defaults={'easydita_resource_id': data['resource_id']},
        )
        webhook.bundle = bundle
        if created or bundle.is_complete():
            logger.info('Webhook accepted')
            webhook.status = Webhook.STATUS_ACCEPTED
            webhook.save()
            bundle.status = Bundle.STATUS_QUEUED
            bundle.time_queued = now()
            bundle.save()
            process_queue.delay()
        else:
            logger.info('Webhook rejected (already processing)')
            webhook.status = Webhook.STATUS_REJECTED
    else:
        logger.info('Webhook rejected (not dita-ot success)')
        webhook.status = Webhook.STATUS_REJECTED
    webhook.save()
    logger.info('Processed {}'.format(webhook))


@job('default', timeout=600)
def publish_drafts(bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    bundle = Bundle.objects.get(pk=bundle_pk)
    bundle.status = Bundle.STATUS_PUBLISHING
    bundle.save()
    logger = get_logger(bundle)
    logger.info(
        'Publishing drafts for easyDITA bundle {}'.format(bundle_pk)
    )
    salesforce = Salesforce()
    s3 = S3()
    n_articles = bundle.articles.count()
    for n, article in enumerate(bundle.articles.all(), start=1):
        logger.info('Publishing article {} of {}: {}'.format(
            n,
            n_articles,
            article,
        ))
        try:
            salesforce.publish_draft(article.kav_id)
        except Exception as e:
            bundle.set_error(e)
            raise
    n_images = bundle.images.count()
    for n, image in enumerate(bundle.images.all(), start=1):
        logger.info('Publishing image {} of {}: {}'.format(
            n,
            n_images,
            image,
        ))
        s3.copy_to_production(image.filename)
    bundle.status = Bundle.STATUS_PUBLISHED
    bundle.time_published = now()
    bundle.save()
    logger.info('Published all drafts for {}'.format(bundle))
    process_queue.delay()
