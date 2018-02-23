from io import BytesIO
import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
import requests

from .html import HTML
from .html import scrub_html
from .logger import get_logger
from .utils import skip_file
from .utils import unzip


class Article(models.Model):
    """Tracks created/updated articles per bundle."""
    draft_preview_url = models.CharField(max_length=255, default='')
    easydita_bundle = models.ForeignKey(
        'EasyditaBundle',
        on_delete=models.CASCADE,
        related_name='articles',
    )
    ka_id = models.CharField(max_length=18)
    kav_id = models.CharField(max_length=18)
    title = models.CharField(max_length=255, default='')
    url_name = models.CharField(max_length=255, default='')

    def __str__(self):
        return '{} ({})'.format(self.title, self.url_name)


class EasyditaBundle(models.Model):
    """Represents a ZIP file of HTML and images from easyDITA."""
    STATUS_NEW = 'N'            # newly received webhook from easyDITA
    STATUS_QUEUED = 'Q'         # added to processing queue
    STATUS_PROCESSING = 'C'     # processing bundle to upload drafts
    STATUS_DRAFT = 'D'          # drafts uploaded and ready for review
    STATUS_REJECTED = 'R'       # drafts have been rejected
    STATUS_PUBLISHING = 'G'     # drafts are being published
    STATUS_PUBLISHED = 'P'      # drafts have been published
    STATUS_ERROR = 'E'          # error processing bundle
    easydita_id = models.CharField(max_length=255, unique=True)
    easydita_resource_id = models.CharField(max_length=255)
    error_message = models.TextField(default='')
    logs = GenericRelation('Log')
    status = models.CharField(
        max_length=1,
        choices=(
            (STATUS_NEW, 'New'),
            (STATUS_QUEUED, 'Queued'),
            (STATUS_PROCESSING, 'Processing'),
            (STATUS_DRAFT, 'Ready for Review'),
            (STATUS_REJECTED, 'Rejected'),
            (STATUS_PUBLISHING, 'Publishing'),
            (STATUS_PUBLISHED, 'Published'),
            (STATUS_ERROR, 'Error'),
        ),
        default=STATUS_NEW,
    )
    time_queued = models.DateTimeField(null=True, blank=True)
    time_processed = models.DateTimeField(null=True, blank=True)
    time_published = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return 'easyDITA bundle {}'.format(self.pk)

    def is_complete(self):
        return self.status in (
            self.STATUS_PUBLISHED,
            self.STATUS_REJECTED,
            self.STATUS_ERROR,
        )

    def download(self, path):
        """Download bundle ZIP and extract to given directory."""
        logger = get_logger(self)
        logger.info('Downloading easyDITA bundle from {}'.format(self.url))
        auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
        response = requests.get(self.url, auth=auth)
        zip_file = BytesIO(response.content)
        unzip(zip_file, path, recursive=True)

    def get_absolute_url(self):
        return '/publish/bundles/{}/'.format(self.pk)

    def process(self, path, salesforce, s3):
        logger = get_logger(self)
        # check all HTML files
        logger.info('Scrubbing all HTML files in {}'.format(self))
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if skip_file(filename):
                    logger.info('Skipping file: {}'.format(filename))
                    continue
                name, ext = os.path.splitext(filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    filename_full = os.path.join(dirpath, filename)
                    logger.info('Scrubbing file: {}'.format(filename_full))
                    with open(filename_full, 'r') as f:
                        html = f.read()
                    scrub_html(html)
        # upload draft articles and images
        logger.info('Uploading draft articles and images')
        publish_queue = []
        changed = False
        images = set([])
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if skip_file(filename):
                    logger.info('Skipping file: {}'.format(filename))
                    continue
                name, ext = os.path.splitext(filename)
                filename_full = os.path.join(dirpath, filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    logger.info('Processing HTML file: {}'.format(filename_full))
                    with open(filename_full, 'r') as f:
                        html_raw = f.read()
                    html = HTML(html_raw)
                    for image_path in html.get_image_paths():
                        images.add(os.path.abspath(os.path.join(
                            dirpath,
                            image_path,
                        )))
                    changed_1 = salesforce.process_article(html, self)
                    if changed_1:
                        changed = True
        for image in images:
            logger.info('Processing image: {}'.format(image))
            changed_1 = s3.process_image(image, self)
            if changed_1:
                changed = True
        if changed:
            self.status = self.STATUS_DRAFT
        else:
            self.status = self.STATUS_REJECTED
            self.error_message = (
                'No articles or images were updated, so the bundle was '
                'automatically rejected.'
            )
        self.save()

    def set_error(self, e, filename=None):
        """Set error status and message."""
        self.status = self.STATUS_ERROR
        if filename:
            self.error_message = '{}: {}'.format(filename, e)
        else:
            self.error_message = str(e)
        self.save()
        logger = get_logger(self)
        logger.error(self.error_message)

    @property
    def url(self):
        """The easyDITA URL for the bundle."""
        return '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.easydita_id,
        )


class Image(models.Model):
    easydita_bundle = models.ForeignKey(
        'EasyditaBundle',
        on_delete=models.CASCADE,
        related_name='images',
    )
    filename = models.CharField(max_length=255)

    def __str__(self):
        return 'Image {}: {}'.format(self.pk, self.filename)


class Log(models.Model):
    content_object = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    message = models.TextField()
    object_id = models.PositiveIntegerField()
    time = models.DateTimeField(auto_now_add=True)

    def get_message(self):
        return '{} {}'.format(
            self.time.strftime('%Y-%m-%dT%H:%M'),
            self.message,
        )


class Webhook(models.Model):
    STATUS_NEW = 'N'        # not yet processed
    STATUS_ACCEPTED = 'A'   # webhook added bundle to processing queue
    STATUS_REJECTED = 'R'   # bundle already processing or queued
    body = models.TextField()
    easydita_bundle = models.ForeignKey(
        'EasyditaBundle',
        on_delete=models.CASCADE,
        related_name='webhooks',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=1,
        choices=(
            (STATUS_NEW, 'New'),
            (STATUS_ACCEPTED, 'Accepted'),
            (STATUS_REJECTED, 'Rejected'),
        ),
        default=STATUS_NEW,
    )
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Webhook {}'.format(self.pk)
