from io import BytesIO
import logging
import os

from django.conf import settings
from django.db import models
import requests

from .exceptions import HtmlError
from .html import scrub_html
from .utils import unzip

logger = logging.getLogger(__name__)


class Article(models.Model):
    """Tracks created/updated articles per bundle."""
    draft_preview_url = models.CharField(max_length=255, default='')
    easydita_bundle = models.ForeignKey(
        'EasyditaBundle',
        on_delete=models.CASCADE,
        related_name='articles',
    )
    kav_id = models.CharField(max_length=18)
    title = models.CharField(max_length=255, default='')
    url_name = models.CharField(max_length=255, default='')

    def __str__(self):
        return 'Article {}: {}'.format(self.pk, self.title)


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
    error_message = models.TextField(default='')
    status = models.CharField(
        max_length=1,
        choices=(
            (STATUS_NEW, 'New'),
            (STATUS_QUEUED, 'Queued'),
            (STATUS_PROCESSING, 'Processing'),
            (STATUS_DRAFT, 'Draft'),
            (STATUS_REJECTED, 'Rejected'),
            (STATUS_PUBLISHING, 'Publishing'),
            (STATUS_PUBLISHED, 'Published'),
            (STATUS_ERROR, 'Error'),
        ),
        default=STATUS_NEW,
    )
    time_queued = models.DateTimeField(null=True, blank=True)
    time_processed = models.DateTimeField(null=True, blank=True)

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
        logger.info('Downloading easyDITA bundle from {}'.format(self.url))
        auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
        response = requests.get(self.url, auth=auth)
        zip_file = BytesIO(response.content)
        unzip(zip_file, path, recursive=True)

    def get_absolute_url(self):
        return '/publish/{}/'.format(self.pk)

    def process(self, path, salesforce, s3):
        # check all HTML files
        logger.info('Scrubbing all HTML files in easyDITA bundle {}'.format(
            self.pk,
        ))
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    filename_full = os.path.join(dirpath, filename)
                    with open(filename_full, 'r') as f:
                        html = f.read()
                    try:
                        scrub_html(html)
                    except HtmlError as e:
                        self.set_error(e)
                        raise
        # upload draft articles and images
        logger.info('Uploading draft articles and images')
        publish_queue = []
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename == 'index.html':
                    continue
                name, ext = os.path.splitext(filename)
                filename_full = os.path.join(dirpath, filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    with open(filename_full, 'r') as f:
                        html = f.read()
                    salesforce.process_article(html, self)
                elif ext.lower() in settings.IMAGE_EXTENSIONS:
                    s3.process_image(filename_full, self)

    def set_error(self, e):
        """Set error status and message."""
        logger.error(str(e))
        self.status = self.STATUS_ERROR
        self.error_message = str(e)
        self.save()

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
