from io import BytesIO
import json
import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django.utils.timezone import now
from django_rq import job
import requests

from .amazon import S3
from .exceptions import SfdocError
from .html import HTML
from .logger import get_logger
from .models import Article
from .models import Bundle
from .models import Image
from .models import Webhook
from .salesforce import Salesforce
from .logger import get_logger
from .utils import is_html
from .utils import skip_html_file
from .utils import unzip


def _process_bundle(bundle, path):
    logger = get_logger(bundle)
    # get APIs
    salesforce = Salesforce()
    s3 = S3()
    # download bundle
    logger.info('Downloading easyDITA bundle from %s', bundle.url)
    auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
    response = requests.get(bundle.url, auth=auth)
    zip_file = BytesIO(response.content)
    unzip(zip_file, path, recursive=True)
    # collect paths to all HTML files
    html_files = []
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filename_full = os.path.join(dirpath, filename)
            if is_html(filename):
                if skip_html_file(filename):
                    logger.info(
                        'Skipping file: %s',
                        filename_full.replace(path + os.sep, ''),
                    )
                    continue
                html_files.append(filename_full)
    # check all HTML files and create list of image files
    html_map = {}
    images = set([])
    logger.info('Scrubbing all HTML files in %s', bundle)
    for n, html_file in enumerate(html_files, start=1):
        logger.info('Scrubbing HTML file %d of %d: %s',
            n,
            len(html_files),
            html_file.replace(path + os.sep, ''),
        )
        with open(html_file) as f:
            html_raw = f.read()
        html = HTML(html_raw)
        html.scrub()
        for image_path in html.get_image_paths():
            images.add(os.path.abspath(os.path.join(
                os.path.dirname(html_file),
                image_path,
            )))
        url_name = html.url_name.lower()
        if url_name not in html_map:
            html_map[url_name] = []
        html_map[url_name].append(html_file)
    # check for duplicate URL names
    if any(map(lambda x: len(x) > 1, html_map.values())):
        msg = 'Found URL name duplicates:'
        for url_name in sorted(html_map.keys()):
            if len(html_map[url_name]) == 1:
                continue
            msg += '\n{}'.format(url_name)
            for html_file in sorted(html_map[url_name]):
                msg += '\n\t{}'.format(html_file)
        raise SfdocError(msg)
    # check for duplicate image filenames
    image_map = {}
    duplicate_images = False
    for image in images:
        basename = os.path.basename(image).lower()
        if basename not in image_map:
            image_map[basename] = []
        image_map[basename].append(image)
        if len(image_map[basename]) > 1:
            duplicate_images = True
    if duplicate_images:
        msg = 'Found image duplicates:'
        for basename in sorted(image_map.keys()):
            msg += '\n{}'.format(basename)
            for image in sorted(image_map[basename]):
                msg += '\n\t{}'.format(image)
        raise SfdocError(msg)
    # build list of published articles to archive
    for article in salesforce.get_articles('online'):
        if article['UrlName'] not in html_map:
            Article.objects.create(
                bundle=bundle,
                ka_id=article['KnowledgeArticleId'],
                kav_id=article['Id'],
                status=Article.STATUS_DELETED,
                title=article['Title'],
                url_name=article['UrlName'],
                preview_url=salesforce.get_preview_url(
                    article['KnowledgeArticleId'],
                ),
            )
    # build list of images to delete
    for obj in s3.iter_objects():
        if (
            not obj['Key'].startswith(settings.AWS_S3_DRAFT_DIR) and
            obj['Key'] not in image_map
        ):
            Image.objects.create(
                bundle=bundle,
                filename=obj['Key'],
                status=Image.STATUS_DELETED,
            )
    # upload draft articles and images
    logger.info('Uploading draft articles and images')
    publish_queue = []
    # process HTML files
    for n, html_file in enumerate(html_files, start=1):
        logger.info('Processing HTML file %d of %d: %s',
            n,
            len(html_files),
            html_file.replace(path + os.sep, ''),
        )
        with open(html_file) as f:
            html_raw = f.read()
        html = HTML(html_raw)
        salesforce.process_article(html, bundle)
    # process images
    for n, image in enumerate(images, start=1):
        logger.info('Processing image file %d of %d: %s',
            n,
            len(images),
            image.replace(path + os.sep, ''),
        )
        s3.process_image(image, bundle)
    if not bundle.articles.count() and not bundle.images.count():
        raise SfdocError('No articles or images changed')
    bundle.status = bundle.STATUS_DRAFT
    bundle.save()


def _publish_drafts(bundle):
    logger = get_logger(bundle)
    salesforce = Salesforce()
    s3 = S3()
    def proc(objects, fun, args, log_prefix):
        N = objects.count()
        for n, obj in enumerate(objects.all(), start=1):
            logger.info('%s %d of %d: %s', log_prefix, n, N, obj)
            fun(*args)
    # publish articles
    proc(
        bundle.articles.filter(status__in=[
            Article.STATUS_NEW,
            Article.STATUS_CHANGED,
        ]),
        salesforce.publish_draft,
        [article.kav_id],
        'Publishing article',
    )
    # publish images
    proc(
        bundle.images.filter(status__in=[
            Image.STATUS_NEW,
            Image.STATUS_CHANGED,
        ]),
        s3.copy_to_production,
        [image.filename],
        'Publishing image',
    )
    # archive articles
    proc(
        bundle.articles.filter(status=Article.STATUS_DELETED),
        salesforce.archive,
        [article.ka_id, article.kav_id],
        'Archiving article',
    )
    # delete images
    proc(
        bundle.images.filter(status=Image.STATUS_DELETED),
        s3.delete,
        [image.filename],
        'Deleting image',
    )


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
    logger.info('Processing %s', bundle)
    with TemporaryDirectory() as tempdir:
        try:
            _process_bundle(bundle, tempdir)
        except Exception as e:
            bundle.set_error(e)
            process_queue.delay()
            raise
    logger.info('Processed %s', bundle)


@job
def process_queue():
    """Process the next easyDITA bundle in the queue."""
    s3 = S3()
    s3.delete_draft_images()
    if Bundle.objects.filter(status__in=(
        Bundle.STATUS_PROCESSING,
        Bundle.STATUS_DRAFT,
        Bundle.STATUS_PUBLISHING,
    )):
        return
    bundles = Bundle.objects.filter(status=Bundle.STATUS_QUEUED)
    if bundles:
        process_bundle.delay(bundles.earliest('time_queued').pk)


@job
def process_webhook(pk):
    """Process an easyDITA webhook."""
    webhook = Webhook.objects.get(pk=pk)
    logger = get_logger(webhook)
    logger.info('Processing %s', webhook)
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
            bundle.queue()
            process_queue.delay()
        else:
            logger.info('Webhook rejected (already processing)')
            webhook.status = Webhook.STATUS_REJECTED
    else:
        logger.info('Webhook rejected (not dita-ot success)')
        webhook.status = Webhook.STATUS_REJECTED
    webhook.save()
    logger.info('Processed %s', webhook)


@job('default', timeout=600)
def publish_drafts(bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    bundle = Bundle.objects.get(pk=bundle_pk)
    bundle.status = Bundle.STATUS_PUBLISHING
    bundle.save()
    logger = get_logger(bundle)
    logger.info('Publishing drafts for %s', bundle)
    try:
        self._publish_drafts(bundle)
    except Exception as e:
        bundle.set_error(e)
        process_queue.delay()
        raise
    bundle.status = Bundle.STATUS_PUBLISHED
    bundle.time_published = now()
    bundle.save()
    logger.info('Published all drafts for %s', bundle)
    process_queue.delay()
