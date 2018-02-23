import json
from tempfile import TemporaryDirectory

from django.utils.timezone import now
from django_rq import job

from .amazon import S3
from .exceptions import SalesforceError
from .models import EasyditaBundle
from .models import Webhook
from .salesforce import Salesforce


@job('default', timeout=600)
def process_easydita_bundle(easydita_bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = EasyditaBundle.STATUS_PROCESSING
    easydita_bundle.time_processed = now()
    easydita_bundle.save()
    logger = get_logger(easydita_bundle)
    logger.info('Processing easyDITA bundle {}'.format(easydita_bundle_pk))
    salesforce = Salesforce()
    s3 = S3()
    with TemporaryDirectory() as tempdir:
        easydita_bundle.download(tempdir)
        try:
            easydita_bundle.process(tempdir, salesforce, s3)
        except Exception as e:
            easydita_bundle.set_error(e)
            raise
    logger.info('Processed {}'.format(easydita_bundle))


@job
def process_queue():
    """Process the next easyDITA bundle in the queue."""
    if EasyditaBundle.objects.filter(status__in=(
        EasyditaBundle.STATUS_PROCESSING,
        EasyditaBundle.STATUS_DRAFT,
        EasyditaBundle.STATUS_PUBLISHING,
    )):
        return
    try:
        easydita_bundle = EasyditaBundle.objects.filter(
            status=EasyditaBundle.STATUS_QUEUED,
        ).earliest('time_queued')
    except EasyditaBundle.DoesNotExist as e:
        return
    process_easydita_bundle.delay(easydita_bundle.pk)


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
    logger.info('Processed {}'.format(webhook))


@job('default', timeout=600)
def publish_drafts(easydita_bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHING
    easydita_bundle.save()
    logger = get_logger(easydita_bundle)
    logger.info(
        'Publishing drafts for easyDITA bundle {}'.format(easydita_bundle_pk)
    )
    salesforce = Salesforce()
    s3 = S3()
    n_articles = easydita_bundle.articles.count()
    for n, article in enumerate(easydita_bundle.articles.all(), start=1):
        logger.info('Publishing article {} of {}: {}'.format(
            n,
            n_articles,
            article,
        ))
        try:
            salesforce.publish_draft(article.kav_id)
        except Exception as e:
            easydita_bundle.set_error(e)
            raise
    n_images = easydita_bundle.images.count()
    for n, image in enumerate(easydita_bundle.images.all(), start=1):
        logger.info('Publishing image {} of {}: {}'.format(
            n,
            n_images,
            image,
        ))
        s3.copy_to_production(image.filename)
    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHED
    easydita_bundle.time_published = now()
    easydita_bundle.save()
    logger.info('Published all drafts for {}'.format(easydita_bundle))
    process_queue.delay()
