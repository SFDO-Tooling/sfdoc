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
from .html import HTML, collect_html_paths
from .logger import get_logger
from .models import Article
from .models import Bundle
from .models import Image
from .models import Webhook
from .salesforce import SalesforceArticles
from . import utils


def _download_and_unpack_easydita_bundle(bundle, path):
    logger = get_logger(bundle)

    logger.info('Downloading easyDITA bundle from %s', bundle.url)
    assert bundle.url.startswith("https://")
    auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
    response = requests.get(bundle.url, auth=auth)
    zip_file = BytesIO(response.content)
    utils.unzip(zip_file, path, recursive=True, ignore_patterns=["*/assets/*"])

def _process_bundle(bundle, path):
    logger = get_logger(bundle)

    # get APIs
    salesforce_docset = SalesforceArticles(bundle.docset_id)
    s3 = S3(bundle)

    s3.delete_draft_images()

    assert os.path.exists(path)

    # get new files from EasyDITA and put them on top
    _download_and_unpack_easydita_bundle(bundle, path)

    path = utils.find_bundle_root_directory(path)

    # name docset for SFDoc UI and 
    extract_docset_metadata_from_index_doc(bundle.docset, path)

    # collect paths to all HTML files
    html_files = collect_html_paths(path, logger)

    create_drafts(bundle, html_files, path, salesforce_docset, s3)

    bundle.status = bundle.STATUS_DRAFT
    bundle.save()


def extract_docset_metadata_from_index_doc(docset, path):
    """Try to name a docset from information in an index HTML"""
    logger = get_logger(docset)
    logger.info("Trying to name docset: %s", docset)
    for dirpath, dirnames, filenames in os.walk(path):
        html_files = [filename for filename in filenames if ".htm" in filename]
        if html_files:
            if len(html_files) > 1:
                raise Exception(f"Multiple index files found in {path}")
            index_file = os.path.join(dirpath, html_files[0])
            html = HTML(index_file, path)
            article_data = html.create_article_data()
            docset.name = article_data['Title']  # for SFDoc UI
            if docset.index_article_url != article_data['UrlName']:
                docset.index_article_url = article_data['UrlName']  # To find the ka_id later 4 Hub_Product_Description
                docset.index_article_ka_id = None          # Clear this to remember to update it later
            docset.save()
            assert docset.index_article_url, f"No UrlName found in {index_file}"
            logger.info("Named: %s, %s", docset.name, docset.index_article_url)

            return
        else:
            raise Exception("No index file found in " + path)


def _find_duplicate_urls(url_map):
    problems = []
    if any(len(x) > 1 for x in url_map.values()):
        msg = "Found URL name duplicates:"
        for url_name, html_files in sorted(url_map.items()):
            if len(url_map[url_name]) == 1:
                continue
            msg += "\n{}".format(url_name)
            for html_file in sorted(html_files):
                msg += "\n\t{}".format(html_file)
        problems.append(msg)
    return problems


def _scrub_and_analyze_html(
    bundle, html_file, path, article_image_map, images, url_map, problems
):
    html = HTML(html_file, path)
    if html.docset_id and html.docset_id != bundle.docset_id:
        problems.append(
            f"HTML ProductMapUUID {html.docset_id} does not match bundle ID, {bundle.docset_id} in {html_file}")

    scrub_problems = html.scrub()
    if scrub_problems:
        problems.extend(scrub_problems)
    article_image_map[html.url_name] = set([])
    for image_path in html.get_image_paths():
        image_path_full = os.path.abspath(
            os.path.join(os.path.dirname(html_file), image_path)
        )
        article_image_map[html.url_name].add(image_path_full)
        images.add(image_path_full)
    url_name = html.url_name.lower()
    if url_name not in url_map:
        url_map[url_name] = []
    url_map[url_name].append(html_file)


def create_drafts(bundle, html_files, path, salesforce_docset, s3):
    # check all HTML files and create list of referenced image files
    logger = get_logger(bundle)
    url_map = {}
    images = set([])
    article_image_map = {}
    logger.info('Scrubbing all HTML files in %s', bundle)
    problems = []
    for n, html_file in enumerate(html_files, start=1):
        logger.info('Scrubbing HTML file %d of %d: %s',
            n,
            len(html_files),
            html_file.replace(path + os.sep, ''),
        )
        _scrub_and_analyze_html(
            bundle, html_file, path, article_image_map, images, url_map, problems
        )


    # check for duplicate URL names
    problems.extend(_find_duplicate_urls(url_map))


    # give up if there are problems before we start making database
    # objects
    if problems:
        for problem in problems:
            logger.info("ERROR! %s", problem)
        raise SfdocError(repr(problems))

    _record_archivable_articles(salesforce_docset, bundle, url_map)

    _record_deletable_images(s3, path, images, bundle)

    # upload draft articles and images
    logger.info('Uploading draft articles and images')
    # process HTML files

    # NOTE: there is a major optimization opportunity here: we could collect
    #       information about what to do on SF and then make a single batch
    #       update call.
    for n, html_file in enumerate(html_files, start=1):
        logger.info('Processing HTML file %d of %d: %s',
            n,
            len(html_files),
            html_file.replace(path + os.sep, ''),
        )
        html = HTML(html_file, path)
        salesforce_docset.process_draft(html, bundle)
    # process images
    for n, image in enumerate(images, start=1):
        logger.info('Processing image file %d of %d: %s',
            n,
            len(images),
            image.replace(path + os.sep, ''),
        )
        s3.process_image(image, path)
    # error if nothing changed
    if not bundle.articles.count() and not bundle.images.count():
        raise SfdocError('No articles or images changed')
    # finish


def _record_archivable_articles(salesforce_docset, bundle, url_map):
    # build list of published articles to archive
    for article in salesforce_docset.get_articles("online"):
        if article["UrlName"].lower() not in url_map:
            Article.objects.create(
                bundle=bundle,
                kav_id=article["Id"],
                status=Article.STATUS_DELETED,
                title=article["Title"],
                url_name=article["UrlName"],
            )


def _record_deletable_images(s3, root_path, images, bundle):
    # build list of images to delete
    logger = get_logger(bundle)
    s3_prefix = Image.get_docset_s3_path(bundle.docset_id, draft=False)
    for obj in s3.iter_objects(s3_prefix):
        objkey = obj["Key"]
        relname = objkey[len(s3_prefix):]
        local_path = os.path.join(root_path, relname)
        if local_path not in images:
            Image.objects.create(
                bundle=bundle, filename=relname, status=Image.STATUS_DELETED
            )
            draftkey = Image.public_url_or_path_to_draft(relname)
            logger.info("Removing orphaned image %s", draftkey)
            s3.delete(draftkey, draft=True)


def _publish_drafts(bundle):
    logger = get_logger(bundle)
    salesforce_docset = SalesforceArticles(bundle.docset_id)
    s3 = S3(bundle)
    # publish articles
    articles = bundle.articles.filter(status__in=[
        Article.STATUS_NEW,
        Article.STATUS_CHANGED,
    ])
    N = articles.count()
    for n, article in enumerate(articles.all(), start=1):
        logger.info('Publishing article %d of %d: %s', n, N, article)
        salesforce_docset.publish_draft(article.kav_id)
    # publish images
    images = bundle.images.filter(status__in=[
        Image.STATUS_NEW,
        Image.STATUS_CHANGED,
    ])
    salesforce_docset.set_docset_index(bundle.docset)
    N = images.count()
    for n, image in enumerate(images.all(), start=1):
        logger.info('Publishing image %d of %d: %s', n, N, image)
        s3.copy_to_production(image.filename)
    # archive articles
    articles = bundle.articles.filter(status=Article.STATUS_DELETED)
    N = articles.count()
    for n, article in enumerate(articles.all(), start=1):
        logger.info('Archiving article %d of %d: %s', n, N, article)
        salesforce_docset.archive(article.kav_id)
    # delete images
    images = bundle.images.filter(status=Image.STATUS_DELETED)
    N = images.count()
    for n, image in enumerate(images.all(), start=1):
        logger.info('Deleting image %d of %d: %s', n, N, image)
        s3.delete(image.filename, draft=False)


@job("default", timeout=600)
def process_bundle(bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    if isinstance(bundle_pk, Bundle):
        bundle = bundle_pk
    else:
        bundle = Bundle.objects.get(pk=bundle_pk)
    assert bundle.status == bundle.STATUS_PROCESSING,\
        "Bundle should be queued before we process it, not {bundle.status}"

    bundle.time_processed = now()
    bundle.save()
    logger = get_logger(bundle)
    logger.info('Processing %s', bundle)

    with TemporaryDirectory(f"bundle_{bundle.pk}") as tempdir:
        try:
            _process_bundle(
                bundle, tempdir
            )
        except Exception as e:
            bundle.set_error(e)
            raise
        finally:
            process_bundle_queues.delay()

    logger.info('Processed %s', bundle)


@job
def process_bundle_queues():
    """Process the next easyDITA bundle in the queue."""
    bundles = Bundle.objects.filter(status=Bundle.STATUS_QUEUED)
    if bundles:
        # ordered dict instead of set to preserve order and simplify testing
        relevant_docsets = {bundle.easydita_resource_id: bundle.easydita_resource_id for bundle in bundles}
        relevant_docsets = relevant_docsets.keys()
        for docset_id in relevant_docsets:
            bundles_for_docset = bundles.filter(easydita_resource_id=docset_id)

            docset_bundles_being_processed_already = Bundle.objects.filter(
                    status__in=(
                        Bundle.STATUS_PROCESSING,
                        Bundle.STATUS_DRAFT,
                        Bundle.STATUS_PUBLISH_WAIT,
                        Bundle.STATUS_PUBLISHING,
                    ), easydita_resource_id=docset_id)
            if not any(docset_bundles_being_processed_already):
                queued_bundles_for_docset = bundles_for_docset.filter(status=Bundle.STATUS_QUEUED)
                bundle_to_process = queued_bundles_for_docset.earliest('time_queued')
                bundle_to_process.status = Bundle.STATUS_PROCESSING
                bundle_to_process.save()
                process_bundle.delay(bundle_to_process.pk)


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
        bundle = Bundle.objects.create(
            easydita_id=data['event_data']['output-uuid'],
            easydita_resource_id=data['resource_id'],
        )
        webhook.bundle = bundle
        logger.info('Webhook accepted')
        webhook.status = Webhook.STATUS_ACCEPTED
        webhook.save()
        bundle.enqueue()
        process_bundle_queues.delay()
    else:
        logger.info('Webhook rejected (not dita-ot success)')
        webhook.status = Webhook.STATUS_REJECTED
    webhook.save()
    logger.info('Processed %s', webhook)


@job('default', timeout=600)
def publish_drafts(bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    if isinstance(bundle_pk, Bundle):
        bundle = bundle_pk
    else:
        bundle = Bundle.objects.get(pk=bundle_pk)

    logger = get_logger(bundle)
    logger.info('Publishing drafts for %s', bundle)
    try:
        assert (
            bundle.status in (bundle.STATUS_DRAFT, bundle.STATUS_PUBLISH_WAIT)
        ), f"Bundle status should not be {dict(bundle.status_names)[bundle.status]}"
        bundle.status = Bundle.STATUS_PUBLISHING
        bundle.save()

        _publish_drafts(bundle)
    except Exception as e:
        bundle.set_error(e)
        logger.info(str(e))
        process_bundle_queues.delay()
        raise
    bundle.status = Bundle.STATUS_PUBLISHED
    bundle.time_published = now()
    bundle.save()
    logger.info('Published all drafts for %s', bundle)
    process_bundle_queues.delay()
