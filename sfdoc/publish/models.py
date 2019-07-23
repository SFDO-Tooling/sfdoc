from traceback import format_exception
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now

from .logger import get_logger


class Article(models.Model):
    """Tracks created/updated articles per bundle."""
    class Meta:
        unique_together = [["bundle", "url_name"]]
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
        related_name='articles',
    )
    ka_id = models.CharField(max_length=18)
    kav_id = models.CharField(max_length=18)
    title = models.CharField(max_length=255, default='')
    url_name = models.CharField(max_length=255, default='')

    def __str__(self):
        return '{} ({}) - {} : {}'.format(self.title, self.url_name, self.status, self.bundle)

    @property
    def docset_id(self):
        return self.bundle.docset_id

    @property
    def preview_url(self):
        return '{}?id={}{}'.format(
            settings.SALESFORCE_ARTICLE_PREVIEW_URL_PATH_PREFIX,
            self.ka_id,
            '&preview=true&pubstatus=d&channel=APP'
        )


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
    easydita_id = models.CharField(max_length=255, unique=False)
    easydita_resource_id = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default='(no description)')
    error_message = models.TextField(default='', blank=True)
    logs = GenericRelation('Log')
    status_names = (
            (STATUS_NEW, 'New'),
            (STATUS_QUEUED, 'Queued'),
            (STATUS_PROCESSING, 'Processing'),
            (STATUS_DRAFT, 'Ready for Review'),
            (STATUS_REJECTED, 'Rejected'),
            (STATUS_PUBLISHING, 'Publishing'),
            (STATUS_PUBLISHED, 'Published'),
            (STATUS_ERROR, 'Error'),
        )
    status = models.CharField(
        max_length=1,
        choices=status_names,
        default=STATUS_NEW,
    )
    time_queued = models.DateTimeField(null=True, blank=True)
    time_processed = models.DateTimeField(null=True, blank=True)
    time_published = models.DateTimeField(null=True, blank=True)
    time_last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'easyDITA bundle {} - {}'.format(self.pk, self.docset.name)

    def is_complete(self):
        return self.status in (
            self.STATUS_PUBLISHED,
            self.STATUS_REJECTED,
            self.STATUS_ERROR,
        )

    def get_absolute_url(self):
        return '/publish/bundles/{}/'.format(self.pk)

    def enqueue(self):
        assert self.status == self.STATUS_NEW
        self.status = self.STATUS_QUEUED
        self.time_queued = now()
        self.save()

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

    @property
    def docset_id(self):
        return self.easydita_resource_id

    @property
    def docset(self):
        return Docset.get_or_create_by_docset_id(self.docset_id)


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

    @staticmethod
    def get_docset_s3_path(docset_id, draft):
        assert isinstance(draft, bool), type(draft)
        if draft:
            status_directory = settings.AWS_S3_DRAFT_IMG_DIR
        else:
            status_directory = settings.AWS_S3_PUBLIC_IMG_DIR

        assert status_directory.endswith("/")

        docset_path = urljoin(status_directory, docset_id) + "/"
        return docset_path

    @staticmethod
    def get_storage_path(docset_id, imagepath, draft):
        fullpath = urljoin(Image.get_docset_s3_path(docset_id, draft), imagepath)
        return fullpath

    @staticmethod
    def get_url(docset_id, imagepath, draft):
        images_root_url = 'https://{}.s3.amazonaws.com/'.format(
            settings.AWS_S3_BUCKET,
        )

        return f"{images_root_url}{(Image.get_storage_path(docset_id, imagepath, draft))}"

    # Draft images are located in settings.AWS_S3_DRAFT_IMG_DIR
    # Production images are located in settings.AWS_S3_PUBLIC_IMG_DIR
    @staticmethod
    def draft_url_or_path_to_public(draft_storage_path):
        return draft_storage_path.replace(settings.AWS_S3_DRAFT_IMG_DIR,
                                          settings.AWS_S3_PUBLIC_IMG_DIR)

    @staticmethod
    def public_url_or_path_to_draft(draft_storage_path):
        return draft_storage_path.replace(settings.AWS_S3_PUBLIC_IMG_DIR,
                                          settings.AWS_S3_DRAFT_IMG_DIR)

    def _get_url(self, draft):
        return Image.get_url(self.docset_id, self.filename, draft)

    @property
    def draft_storage_path(self):
        return Image.get_storage_path(self.docset_id, self.filename, draft=True)

    @property
    def public_storage_path(self):
        return Image.get_storage_path(self.docset_id, self.filename, draft=False)

    @property
    def url_draft(self):
        return self._get_url(True)

    @property
    def url_production(self):
        return self._get_url(False)

    @property
    def docset_id(self):
        return self.bundle.docset_id


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

    @property
    def docset_id(self):
        return self.bundle.docset_id


class Docset(models.Model):
    docset_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255, default='')
    index_article_url = models.CharField(
        max_length=255,
        null=True,
    )
    index_article_ka_id = models.CharField(
        max_length=64,
        null=True,
    )

    @classmethod
    def get_or_create_by_docset_id(cls, docset_id):
        obj, created = cls.objects.get_or_create(docset_id=docset_id)
        return obj

    @property
    def display_name(self):
        return self.name or self.docset_id
