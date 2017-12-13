from io import BytesIO
from zipfile import ZipFile

from bs4 import BeautifulSoup
from bs4 import Comment
from django.conf import settings
from django.db import models
import requests
from simple_salesforce.exceptions import SalesforceGeneralError

from .exceptions import HtmlError
from .exceptions import KnowledgeError
from .salesforce import get_salesforce_api


class Article(models.Model):
    body = models.TextField(null=True)
    body_new = models.TextField(null=True)
    html = models.TextField(null=True)
    html_hash = models.CharField(max_length=255, null=True)
    html_new = models.TextField(null=True)
    last_updated_by = models.ForeignKey('EasyditaBundle', null=True)
    ready_to_publish = models.BooleanField(default=False)
    salesforce_id = models.CharField(max_length=255, null=True, unique=True)
    salesforce_kav_id = models.CharField(max_length=255, null=True, unique=True)
    summary = models.TextField(null=True)
    summary_new = models.TextField(null=True)
    time_created = models.DateTimeField(auto_now_add=True, null=True)
    title = models.CharField(max_length=255, null=True)
    title_new = models.CharField(max_length=255, null=True)
    url_name = models.CharField(max_length=255, null=True, unique=True)

    @property
    def changed(self):
        """Check if HTML has changed."""
        return False if self.html_hash == hash(self.html_new) else True

    @staticmethod
    def get_url_name(html):
        """Parse article URL name from raw HTML string."""
        soup = BeautifulSoup(html, 'html.parser')
        for meta in soup.find_all('meta'):
            if meta.get('name') == 'UrlName':
                return meta.get('content')

    def parse(self):
        """Parse raw HTML into model fields."""
        soup = BeautifulSoup(self.html_new, 'html.parser')
        # remove all comments (scripts can be run from comments)
        comments = soup.findAll(text=lambda text:isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        for meta in soup('meta'):
            if meta['name'] == 'Summary':
                self.title_new = meta['content']
            elif meta['name'] == 'Title':
                self.title_new = meta['content']
        for div in soup('div'):
            div_class = div.get('class')
            if div_class and 'row-fluid' in div_class:
                self.body_new = div.prettify()

    def reset_fields(self):
        """Set the 'new' fields back to original values for next comparison."""
        self.html_new = self.html
        self.title_new = self.title
        self.summary_new = self.summary
        self.body_new = self.body
        self.save()

    @staticmethod
    def scrub(html):
        """Scrub the HTML file for security."""
        # build the whitelist
        soup = BeautifulSoup(html, 'html.parser')

        def scrub_tree(tree):
            for child in tree.children:
                if hasattr(child, 'contents'):
                    if child.name not in settings.HTML_WHITELIST:
                        raise HtmlError(
                            'Tag "{}" not in whitelist'.format(child.name)
                        )
                    for attr in child.attrs:
                        if attr not in settings.HTML_WHITELIST[child.name]:
                            raise HtmlError(
                                'Tag "{}" attribute "{}" not in whitelist'.format(
                                    child.name,
                                    attr,
                                )
                            )
                        if attr == 'href':
                            o = urlparse(child['href'])
                            if o.hostname not in settings.LINK_WHITELIST:
                                raise HtmlError(
                                    'Link {} not in whitelist'.format(
                                        child['href']
                                    )
                                )
                    scrub_tree(child)
        scrub_tree(soup)

    def update(self):
        """Process HTML and upload a new draft KnowledgeArticleVersion."""
        self.parse()
        self.update_image_links()
        self.upload()

    def update_image_links(self):
        """Replace the image URL placeholder."""
        soup = BeautifulSoup(self.body_new, 'html.parser')
        for img in soup('img'):
            src = img.get('src')
            if src and settings.IMAGES_URL_PLACEHOLDER in src:
                img['src'] = src.replace(
                    settings.IMAGES_URL_PLACEHOLDER,
                    settings.IMAGES_URL_ROOT,
                )
        self.body_new = soup.prettify()
        self.save()

    def upload(self):
        """Upload the article to the Salesforce org as a draft."""
        sf = get_salesforce_api()
        kav_api = getattr(sf, settings.SALESFORCE_ARTICLE_TYPE)
        if self.salesforce_id:
            # new version of existing article
            url = (
                sf.base_url +
                'knowledgeManagement/articleVersions/masterVersions'
            )
            data = {'articleId': self.salesforce_id}
            try:
                result = sf._call_salesforce('POST', url, json=data)
            except SalesforceGeneralError as e:
                if e.status == HTTPStatus.CONFLICT:
                    # draft already exists
                    raise KnowledgeError(
                        'Could not create new version of existing article:\n' +
                        'URL Name: {}\n'.format(self.url_name) +
                        'Title: {}\n'.format(self.title_new) +
                        'Summary: {}\n'.format(self.summary_new) +
                        'Body: {}\n'.format(self.body_new) +
                        'Status: {}\n'.format(e.status) +
                        'Error Code: {}\n'.format(e.content[0]['errorCode']) +
                        'Message: {}\n'.format(e.content[0]['message'])
                    )
            if result.status_code != HTTPStatus.CREATED:
                raise KnowledgeError(
                    'Could not create new version of existing article:\n' +
                    'URL Name: {}\n'.format(self.url_name) +
                    'Title: {}\n'.format(self.title_new) +
                    'Summary: {}\n'.format(self.summary_new) +
                    'Body: {}\n'.format(self.body_new) +
                    'Errors: {}\n'.format(result['errors'])
                )
            kav_id = result.json()['id']
            result = kav_api.update(kav_id, {
                'Title': self.title_new,
                'Summary': self.summary_new,
                settings.SALESFORCE_ARTICLE_BODY_FIELD: self.body_new,
            })
            if result != HTTPStatus.NO_CONTENT:
                raise KnowledgeError('Could not edit article draft')
        else:
            # new article
            result = kav_api.create(data={
                'UrlName': self.url_name,
                'Title': self.title_new,
                'Summary': self.summary_new,
                settings.SALESFORCE_ARTICLE_BODY_FIELD: self.body_new,
            })
            if not result['success']:
                raise KnowledgeError(
                    'Could not create new article:\n' +
                    'URL Name: {}\n'.format(self.url_name) +
                    'Title: {}\n'.format(self.title_new) +
                    'Summary: {}\n'.format(self.summary_new) +
                    'Body: {}\n'.format(self.body_new) +
                    'Errors: {}\n'.format(result['errors'])
                )
            kav_id = result['id']
            kav = kav_api.get(kav_id)
            self.salesforce_id = kav['KnowledgeArticleId']
        self.salesforce_kav_id = kav_id
        self.ready_to_publish = True
        self.save()


class Image(models.Model):
    time_created = models.DateTimeField(auto_now_add=True)
    image_file = models.ImageField()
    image_hash = models.CharField(max_length=255, unique=True)


class EasyditaBundle(models.Model):
    easydita_id = models.CharField(max_length=255, unique=True)
    time_created = models.DateTimeField(auto_now_add=True)

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
