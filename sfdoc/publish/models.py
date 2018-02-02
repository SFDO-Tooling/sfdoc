from io import BytesIO
from zipfile import ZipFile

from django.conf import settings
from django.db import models
import requests


class Article(models.Model):
    """Tracks created/updated articles per bundle."""
    draft_preview_url = models.CharField(
        max_length=255,
        unique=True,
        default='',
    )
    easydita_bundle = models.ForeignKey(
        'EasyditaBundle',
        on_delete=models.CASCADE,
        related_name='articles',
    )
    kav_id = models.CharField(max_length=18, unique=True)


class EasyditaBundle(models.Model):
    """Represents a ZIP file of HTML and images from easyDITA."""
    STATUS_NEW = 'N'            # newly received webhook from easyDITA
    STATUS_QUEUED = 'Q'         # added to processing queue
    STATUS_PROCESSING = 'C'     # processing bundle to upload drafts
    STATUS_DRAFT = 'D'          # drafts uploaded and ready for review
    STATUS_REJECTED = 'R'       # drafts have been rejected
    STATUS_PUBLISHING = 'G'     # drafts are being published
    STATUS_PUBLISHED = 'P'      # drafts have been published
    easydita_id = models.CharField(max_length=255, unique=True)
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
        ),
        default=STATUS_NEW,
    )
    time_queued = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return 'easyDITA bundle {}'.format(self.pk)

    def is_complete(self):
        return self.status in (
            self.STATUS_PUBLISHED,
            self.STATUS_REJECTED,
        )

    def download(self, path):
        """Download bundle ZIP and extract to given directory."""
        auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
        response = requests.get(self.url, auth=auth)
        zip_file = BytesIO(response.content)
        with ZipFile(zip_file) as f:
            f.extractall(path)

    def get_absolute_url(self):
        return '/publish/{}/'.format(self.pk)

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
    filename = models.CharField(max_length=255, unique=True)


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
