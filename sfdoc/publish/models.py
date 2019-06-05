from traceback import format_exception

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now

from .logger import get_logger


class Article(models.Model):
    """Tracks created/updated articles per bundle."""
    STATUS_NEW = 'N'
    STATUS_CHANGED = 'C'
    STATUS_DELETED = 'D'
    status = models.CharField(
        max_length=1,
        choices=(
            (STATUS_NEW, 'New'),
            (STATUS_CHANGED, 'Changed'),
            (STATUS_DELETED, 'Deleted'),
        ),
    )
    preview_url = models.CharField(max_length=255, default='')
    bundle = models.ForeignKey(
        'Bundle',
        on_delete=models.CASCADE,
        related_name='articles',
    )
    ka_id = models.CharField(max_length=18)
    kav_id = models.CharField(max_length=18)
    title = models.CharField(max_length=255, default='')
    url_name = models.CharField(max_length=255, default='')

    def __str__(self):
        return '{} ({})'.format(self.title, self.url_name)


class Bundle(models.Model):
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
    description = models.CharField(max_length=255, default='(no description)')
    error_message = models.TextField(default='', blank=True)
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
    time_last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'easyDITA bundle {}'.format(self.pk)

    def is_complete(self):
        return self.status in (
            self.STATUS_PUBLISHED,
            self.STATUS_REJECTED,
            self.STATUS_ERROR,
        )

    def get_absolute_url(self):
        return '/publish/bundles/{}/'.format(self.pk)

    def queue(self):
        self.status = self.STATUS_QUEUED
        self.time_queued = now()
        self.error_message = ''
        self.save()
        for article in self.articles.all():
            article.delete()
        for image in self.images.all():
            image.delete()

    def set_error(self, e):
        """Set error status and message."""
        tb_list = format_exception(None, e, e.__traceback__)
        self.error_message = ''.join(tb_list)
        self.status = self.STATUS_ERROR
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
    STATUS_NEW = 'N'
    STATUS_CHANGED = 'C'
    STATUS_DELETED = 'D'
    status = models.CharField(
        max_length=1,
        choices=(
            (STATUS_NEW, 'New'),
            (STATUS_CHANGED, 'Changed'),
            (STATUS_DELETED, 'Deleted'),
        ),
    )
    bundle = models.ForeignKey(
        'Bundle',
        on_delete=models.CASCADE,
        related_name='images',
    )
    filename = models.CharField(max_length=255)

    def __str__(self):
        return 'Image {}: {}'.format(self.pk, self.filename)

    def _get_url(self, draft):
        images_path = 'https://{}.s3.amazonaws.com/'.format(
            settings.AWS_S3_BUCKET,
        )
        if draft:
            images_path += settings.AWS_S3_DRAFT_DIR
        return images_path + self.filename

    @property
    def url_draft(self):
        return self._get_url(True)

    @property
    def url_production(self):
        return self._get_url(False)


class Log(models.Model):
    content_object = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    message = models.TextField()
    object_id = models.PositiveIntegerField()
    time = models.DateTimeField(auto_now_add=True)

    def get_message(self):
        return '{} {}'.format(
            self.time.strftime('%Y-%m-%dT%H:%M:%S'),
            self.message,
        )


class Webhook(models.Model):
    STATUS_NEW = 'N'        # not yet processed
    STATUS_ACCEPTED = 'A'   # webhook added bundle to processing queue
    STATUS_REJECTED = 'R'   # bundle already processing or queued
    body = models.TextField()
    bundle = models.ForeignKey(
        'Bundle',
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
