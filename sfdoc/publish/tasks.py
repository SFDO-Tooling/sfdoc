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
from .salesforce import Salesforce
from . import utils

AWS_S3_PUBLISHED_HTML_REPOSITORY_URL = (
    f"s3://{settings.AWS_S3_BUCKET}/{settings.AWS_S3_PUBLISHED_HTML_REPOSITORY_DIR}"
)

AWS_S3_DRAFT_HTML_REPOSITORY_URL = (
    f"s3://{settings.AWS_S3_BUCKET}/{settings.AWS_S3_DRAFT_HTML_REPOSITORY_DIR}"
)


def _download_and_unpack_easydita_bundle(bundle, path):
    logger = get_logger(bundle)

    logger.info("Downloading easyDITA bundle from %s", bundle.url)
    assert bundle.url.startswith("https://")
    auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
    response = requests.get(bundle.url, auth=auth)
    zip_file = BytesIO(response.content)
    with TemporaryDirectory(f"bundle_{bundle.pk}_") as tempdir:
        utils.unzip(zip_file, tempdir, recursive=True, ignore_patterns=["*/assets/*"])

        rootpath = utils.find_bundle_root_directory(tempdir)
        assert os.path.exists(os.path.join(rootpath, "log.txt"))
        utils.sync_directories(rootpath, path)
        assert os.path.exists(os.path.join(path, "log.txt"))


def _process_bundle(bundle, path, enforce_no_duplicates=True):
    logger = get_logger(bundle)

    # TODO remove
    logger.setLevel("INFO")
    # get APIs
    salesforce = Salesforce(bundle.docset_id)
    s3 = S3(bundle)

    s3.delete_draft_images()

    assert os.path.exists(path)

    # get new files from EasyDITA and put them on top
    _download_and_unpack_easydita_bundle(bundle, path)

    # try to name docset if necessary
    if not bundle.docset.name:
        try_name_docset(bundle.docset, path)

    # collect paths to all HTML files
    html_files = collect_html_paths(path, logger)

    create_drafts(bundle, html_files, path, salesforce, s3)


def try_name_docset(docset, path):
    """Try to name a docset from information in an index HTML"""
    for dirpath, dirnames, filenames in os.walk(path):
        html_files = [filename for filename in filenames if ".htm" in filename]
        if html_files:
            index_file = os.path.join(path, html_files[0])
            with open(index_file, "r") as f:
                markup = f.read()
            html = HTML(markup, index_file, path)
            docset.name = html.create_article_data()['Title']
            docset.save()
            return


def _find_duplicate_urls(url_map):
    problems = []
    if any(len(x) > 1 for x in url_map.values()):
        msg = "Found URL name duplicates:"
        for url_name in sorted(url_map.keys()):
            if len(url_map[url_name]) == 1:
                continue
            msg += "\n{}".format(url_name)
            for html_file in sorted(url_map[url_name]):
                msg += "\n\t{}".format(html_file)
        problems.append(msg)
    return problems


def _scrub_and_analyze_html(
    html_file, path, article_image_map, images, url_map, problems
):
    with open(html_file) as f:
        html_raw = f.read()

    html = HTML(html_raw, html_file, path)

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


def create_drafts(bundle, html_files, path, salesforce, s3):
    # check all HTML files and create list of referenced image files
    logger = get_logger(bundle)
    url_map = {}
    images = set([])
    article_image_map = {}
    logger.info("Scrubbing all HTML files in %s", bundle)
    problems = []
    for n, html_file in enumerate(html_files, start=1):
        logger.info(
            "Scrubbing HTML file %d of %d: %s",
            n,
            len(html_files),
            html_file.replace(path + os.sep, ""),
        )
        _scrub_and_analyze_html(
            html_file, path, article_image_map, images, url_map, problems
        )

    # check for duplicate URL names
    problems.extend(_find_duplicate_urls(url_map))

    # give up if there are problems before we start making database
    # objects
    if problems:
        raise SfdocError(repr(problems))

    _record_archivable_articles(salesforce, bundle, url_map)

    _record_deletable_images(s3, path, images, bundle)

    # upload draft articles and images
    logger.info("Uploading draft articles and images")
    # process HTML files
    for n, html_file in enumerate(html_files, start=1):
        logger.info(
            "Processing HTML file %d of %d: %s",
            n,
            len(html_files),
            html_file.replace(path + os.sep, ""),
        )
        with open(html_file) as f:
            html_raw = f.read()
        html = HTML(html_raw, html_file, path)
        salesforce.process_draft(html, bundle)
    # process images
    for n, image in enumerate(images, start=1):
        logger.info(
            "Processing image file %d of %d: %s",
            n,
            len(images),
            image.replace(path + os.sep, ""),
        )
        s3.process_image(image, path)
    # upload unchanged images for article previews
    logger.info("Checking for unchanged images used in draft articles")
    unchanged_images = set([])
    for article in bundle.articles.filter(
        status__in=(Article.STATUS_NEW, Article.STATUS_CHANGED)
    ):
        for image in article_image_map[article.url_name]:
            relpath = utils.bundle_relative_path(path, image)
            if not bundle.images.filter(filename=relpath):
                unchanged_images.add(image)
    for n, image in enumerate(unchanged_images, start=1):
        logger.info(
            "Uploading unchanged image %d of %d: %s", n, len(unchanged_images), image
        )
        relative_filename = utils.bundle_relative_path(path, image)
        key = Image.get_storage_path(bundle.docset_id, relative_filename, draft=True)
        s3.upload_image(image, key)
    # error if nothing changed
    if not bundle.articles.count() and not bundle.images.count():
        raise SfdocError("No articles or images changed")
    # finish
    bundle.status = bundle.STATUS_DRAFT
    bundle.save()
    utils.s3_sync(path, AWS_S3_DRAFT_HTML_REPOSITORY_URL)


def _record_archivable_articles(salesforce, bundle, url_map):
    # build list of published articles to archive
    for article in salesforce.get_articles("online"):
        if article["UrlName"].lower() not in url_map:
            Article.objects.create(
                bundle=bundle,
                ka_id=article["KnowledgeArticleId"],
                kav_id=article["Id"],
                status=Article.STATUS_DELETED,
                title=article["Title"],
                url_name=article["UrlName"],
                preview_url=salesforce.get_preview_url(
                    article["KnowledgeArticleId"], online=True
                ),
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
    salesforce = Salesforce(bundle.docset_id)
    s3 = S3(bundle)
    # publish articles
    articles = bundle.articles.filter(
        status__in=[Article.STATUS_NEW, Article.STATUS_CHANGED]
    )
    N = articles.count()
    for n, article in enumerate(articles.all(), start=1):
        logger.info("Publishing article %d of %d: %s", n, N, article)
        salesforce.publish_draft(article.kav_id)
    # publish images
    images = bundle.images.filter(status__in=[Image.STATUS_NEW, Image.STATUS_CHANGED])
    N = images.count()
    for n, image in enumerate(images.all(), start=1):
        logger.info("Publishing image %d of %d: %s", n, N, image)
        s3.copy_to_production(image.filename)
    # archive articles
    articles = bundle.articles.filter(status=Article.STATUS_DELETED)
    N = articles.count()
    for n, article in enumerate(articles.all(), start=1):
        logger.info("Archiving article %d of %d: %s", n, N, article)
        salesforce.archive(article.ka_id, article.kav_id)
    # delete images
    images = bundle.images.filter(status=Image.STATUS_DELETED)
    N = images.count()
    for n, image in enumerate(images.all(), start=1):
        logger.info("Deleting image %d of %d: %s", n, N, image.filename)
        s3.delete(image.filename, draft=False)

    # update the S3 repository to represent current public state by
    # promoting the draft to prod
    utils.s3_sync(
        AWS_S3_DRAFT_HTML_REPOSITORY_URL,
        AWS_S3_PUBLISHED_HTML_REPOSITORY_URL,
        delete=True,
    )


@job("default", timeout=600)
def process_bundle(bundle_pk, enforce_no_duplicates=True):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    if isinstance(bundle_pk, Bundle):
        bundle = bundle_pk
    else:
        bundle = Bundle.objects.get(pk=bundle_pk)
    bundle.status = Bundle.STATUS_PROCESSING
    bundle.time_processed = now()
    bundle.save()
    logger = get_logger(bundle)
    logger.info("Processing %s", bundle)

    with TemporaryDirectory(f"bundle_{bundle.pk}") as tempdir:
        try:
            _process_bundle(
                bundle, tempdir, enforce_no_duplicates=enforce_no_duplicates
            )
        except Exception as e:
            bundle.set_error(e)
            process_bundle_queues.delay()
            raise
    logger.info("Processed %s", bundle)


@job
def process_bundle_queues():
    """Process the next easyDITA bundle in the queue."""
    if Bundle.objects.filter(
        status__in=(
            Bundle.STATUS_PROCESSING,
            Bundle.STATUS_DRAFT,
            Bundle.STATUS_PUBLISHING,
        )
    ):
        return
    bundles = Bundle.objects.filter(status=Bundle.STATUS_QUEUED)
    if bundles:
        relevant_docsets = set(bundle.easydita_id for bundle in bundles)
        for docset_id in relevant_docsets:
            bundles_for_docset = bundles.filter(easydita_id=docset_id)
            process_bundle.delay(bundles_for_docset.earliest("time_queued").pk)


@job
def process_webhook(pk):
    """Process an easyDITA webhook."""
    webhook = Webhook.objects.get(pk=pk)
    logger = get_logger(webhook)
    logger.info("Processing %s", webhook)
    data = json.loads(webhook.body)
    if (
        data["event_id"] == "dita-ot-publish-complete"
        and data["event_data"]["publish-result"] == "success"
    ):
        bundle, created = Bundle.objects.get_or_create(
            easydita_id=data["event_data"]["output-uuid"],
            defaults={"easydita_resource_id": data["resource_id"]},
        )
        webhook.bundle = bundle
        if created or bundle.is_complete():
            logger.info("Webhook accepted")
            webhook.status = Webhook.STATUS_ACCEPTED
            webhook.save()
            bundle.enqueue()
            process_bundle_queues.delay()
        else:
            logger.info("Webhook rejected (already processing)")
            webhook.status = Webhook.STATUS_REJECTED
    else:
        logger.info("Webhook rejected (not dita-ot success)")
        webhook.status = Webhook.STATUS_REJECTED
    webhook.save()
    logger.info("Processed %s", webhook)


@job("default", timeout=600)
def publish_drafts(bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    if isinstance(bundle_pk, Bundle):
        bundle = bundle_pk
    else:
        bundle = Bundle.objects.get(pk=bundle_pk)
    assert (
        bundle.status == bundle.STATUS_DRAFT
    ), f"Bundle status should not be {dict(bundle.status_names)[bundle.status]}"
    bundle.status = Bundle.STATUS_PUBLISHING
    bundle.save()
    logger = get_logger(bundle)
    logger.info("Publishing drafts for %s", bundle)
    try:
        _publish_drafts(bundle)
    except Exception as e:
        bundle.set_error(e)
        process_bundle_queues.delay()
        raise
    bundle.status = Bundle.STATUS_PUBLISHED
    bundle.time_published = now()
    bundle.save()
    logger.info("Published all drafts for %s", bundle)
    process_bundle_queues.delay()
