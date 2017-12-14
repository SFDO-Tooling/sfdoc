from io import BytesIO
from zipfile import ZipFile

from django.conf import settings
from django.db import models
from django.utils.timezone import now
import requests


class EasyditaBundle(models.Model):
    easydita_id = models.CharField(max_length=255, unique=True)
    time_created = models.DateTimeField(auto_now_add=True)
    last_received = models.DateTimeField(default=now)

    def download(self, path):
        """Download bundle ZIP and extract to given directory."""
        auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
        response = requests.get(self.url, auth=auth)
        zip_file = BytesIO(response.content)
        with ZipFile(zip_file) as f:
            f.extractall(path)

    @property
    def url(self):
        """The easyDITA URL for the bundle."""
        return '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.easydita_id,
        )


class Image(models.Model):
    image_file = models.ImageField()
    image_hash = models.CharField(max_length=255, unique=True)
    time_created = models.DateTimeField(auto_now_add=True)
