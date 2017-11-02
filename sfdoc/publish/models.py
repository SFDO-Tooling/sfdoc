from io import BytesIO
from zipfile import ZipFile

from django.conf import settings
from django.db import models
import requests


class Article(models.Model):
    body = models.TextField()
    html = models.TextField()
    salesforce_id = models.CharField(max_length=255, unique=True)
    time_created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255)
    url_name = models.CharField(max_length=255)


class Image(models.Model):
    time_created = models.DateTimeField(auto_now_add=True)
    image_file = models.ImageField()
    image_hash = models.CharField(max_length=255, unique=True)


class EasyditaBundle(models.Model):
    easydita_id = models.CharField(max_length=255, unique=True)
    time_created = models.DateTimeField(auto_now_add=True)

    def download(self, path):
        auth = (settings.EASYDITA_USERNAME, settings.EASYDITA_PASSWORD)
        response = requests.get(self.url, auth=auth)
        zip_file = BytesIO(response.content)
        with ZipFile(zip_file) as f:
            f.extractall(path)

    @property
    def url(self):
        return '{}/rest/all-files/{}/bundle'.format(
            settings.EASYDITA_INSTANCE_URL,
            self.easydita_id,
        )
