from io import BytesIO
from zipfile import ZipFile

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import models
import requests


class Article(models.Model):
    body = models.TextField(null=True)
    html = models.TextField(null=True)
    html_hash = models.CharField(max_length=255, null=True)
    salesforce_id = models.CharField(max_length=255, null=True, unique=True)
    time_created = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField(max_length=255, null=True)
    url_name = models.CharField(max_length=255, null=True, unique=True)

    @staticmethod
    def get_url_name(html):
        """Parse article URL name from raw HTML string."""
        soup = BeautifulSoup(html, 'html.parser')
        for meta in soup.find_all('meta'):
            if meta.get('name') == 'UrlName':
                return meta.get('content')

    @staticmethod
    def get_whitelist():
        """Build whitelist dict from env var."""
        whitelist = {}
        for item in settings.HTML_WHITELIST.split(';'):
            x = item.split(':')
            assert(len(x) in (1, 2))
            tag = x[0].lower()
            if tag not in whitelist:
                whitelist[tag] = []
            if len(x) == 2:
                attrs = x[1].lower()
                for attr in attrs.split(','):
                    whitelist[tag].append(attr)
        return whitelist

    def parse(self):
        """Parse raw HTML into model fields."""
        soup = BeautifulSoup(self.html, 'html.parser')
        for meta in soup('meta'):
            meta_name = meta.get('name')
            meta_content = meta.get('content')
            if meta_name == 'Title':
                self.title = meta_content
            elif meta_name == 'UrlName':
                self.url_name = meta_content
        for div in soup('div'):
            div_class = div.get('class')
            if div_class and 'row-fluid' in div_class:
                self.body = div.prettify()

    def scrub(self):
        """Scrub the article body for security."""
        whitelist = self.get_whitelist()

        soup = BeautifulSoup(self.body, 'html.parser')
        assert(len(soup.contents) == 1)
        assert(soup.contents[0].name == 'div')

        root = soup.contents[0]
        assert(len(root.attrs) == 1)
        assert('class' in root.attrs)
        assert(root['class'] == ['row-fluid'])

        def process_tree(tree):
            for child in tree.children:
                if hasattr(child, 'contents'):
                    assert(child.name in whitelist)
                    for attr in child.attrs:
                        assert(attr in whitelist[child.name])
                    process_tree(child)
                else:
                    # string
                    pass

        process_tree(root)
        self.body = soup.prettify()
        self.save()

    def update(self):
        """Process HTML and update the Knowledge Article."""
        self.parse()
        self.update_image_links()
        self.scrub()
        self.upload()
        self.update_html_hash()

    def update_html_hash(self):
        """Set the html_hash field."""
        self.html_hash = hash(self.html)
        self.save()

    def update_image_links(self):
        """Replace the image URL placeholder."""
        soup = BeautifulSoup(self.body, 'html.parser')
        for img in soup('img'):
            src = img.get('src')
            if src and settings.IMAGES_URL_PLACEHOLDER in src:
                img['src'] = src.replace(
                    settings.IMAGES_URL_PLACEHOLDER,
                    settings.IMAGES_URL_ROOT,
                )
        self.body = soup.prettify()
        self.save()

    def upload(self):
        """Upload the article to the Salesforce org."""
        if self.salesforce_id:
            # article already exists, just add a new KAV
            pass
        else:
            # create a new KA in addition to the KAV
            # set the salesforce_id using new KA when done
            pass


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
