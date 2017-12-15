from io import BytesIO
from zipfile import ZipFile

from django.conf import settings
from django.db import models
import requests


class EasyditaBundle(models.Model):
    easydita_id = models.CharField(max_length=255, unique=True)

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
