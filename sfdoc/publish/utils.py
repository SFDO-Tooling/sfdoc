import filecmp
from http import HTTPStatus
import os
from tempfile import TemporaryDirectory
from urllib.parse import urljoin

import boto3
import botocore
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files import File
from django.core.mail import send_mail

from .exceptions import HtmlError
from .exceptions import KnowledgeError


def get_site_url():
    return 'http://' + settings.HEROKU_APP_NAME


def email(message, easydita_bundle, e=None):
    """Send an email."""
    subject = '[sfdoc] easyDITA bundle {}'.format(easydita_bundle.easydita_id)
    if e:
        message += (
            '\n\n'
            'Error while processing easyDITA bundle:\n'
            '[{}] {}\n'
        ).format(e.__class__.__name__, e)
    message += '\neasyDITA bundle URL: {}\n'.format(easydita_bundle.url)
    send_mail(subject, message, settings.FROM_EMAIL, settings.TO_EMAILS)


def parse(html):
    """Parse article fields from HTML."""
    url_name = title = summary = body = None
    soup = BeautifulSoup(html, 'html.parser')

    # URL name, title, summary
    for meta in soup('meta'):
        name = meta.get('name').lower()
        if not name:
            # not a name/content tag
            continue
        if name == 'urlname':
            url_name = meta['content']
        elif name == 'title':
            title = meta['content']
        elif name == 'summary':
            summary = meta['content']

    # body
    for div in soup('div'):
        div_class = div.get('class')
        if div_class and 'row-fluid' in div_class:
            body = div.prettify()

    return url_name, title, summary, body


def publish_kav(kav_id, sf):
    """Publish a draft KnowledgeArticleVersion."""
    url = (
        sf.base_url +
        'knowledgeManagement/articleVersions/masterVersions/{}'.format(kav_id)
    )
    data = {'publishStatus': 'online'}  # increment minor version
    result = sf._call_salesforce('PATCH', url, json=data)
    if result.status_code != HTTPStatus.NO_CONTENT:
        msg = 'Error publishing KnowledgeArticleVersion (ID={})'.format(kav_id)
        raise KnowledgeError(msg)


def query_kav(sf, url_name, publish_status):
    query_str = (
        "SELECT Id,KnowledgeArticleId,Title,Summary,{} FROM {} "
        "WHERE UrlName='{}' AND PublishStatus='{}' AND language='en_US'"
    ).format(
        settings.SALESFORCE_ARTICLE_BODY_FIELD,
        settings.SALESFORCE_ARTICLE_TYPE,
        url_name,
        publish_status,
    )
    result = sf.query(query_str)
    return result


def replace_image_links(html_body):
    """Replace the image URL placeholder."""
    images_path = urljoin(
        settings.AWS_S3_URL,
        settings.AWS_STORAGE_BUCKET_NAME,
    )
    soup = BeautifulSoup(html_body, 'html.parser')
    for img in soup('img'):
        img['src'] = img['src'].replace(
            settings.IMAGES_URL_PLACEHOLDER,
            images_path,
        )
    return soup.prettify()


def scrub(html):
    """Scrub HTML using whitelists for tags/attributes and links."""
    soup = BeautifulSoup(html, 'html.parser')

    def scrub_tree(tree):
        for child in tree.children:
            if hasattr(child, 'contents'):
                if child.name not in settings.HTML_WHITELIST:
                    msg = 'Tag "{}" not in whitelist'.format(child.name)
                    raise HtmlError(msg)
                for attr in child.attrs:
                    if attr not in settings.HTML_WHITELIST[child.name]:
                        msg = (
                            'Tag "{}" attribute "{}" not in whitelist'
                        ).format(child.name, attr)
                        raise HtmlError(msg)
                    if attr == 'href':
                        o = urlparse(child['href'])
                        if o.hostname not in settings.LINK_WHITELIST:
                            msg = 'Link {} not in whitelist'.format(
                                child['href'],
                            )
                            raise HtmlError(msg)
                scrub_tree(child)
    scrub_tree(soup)


def update_draft(kav_api, kav_id, title, summary, body):
    """Update the fields of an existing draft."""
    data = {
        'Title': title,
        'Summary': summary,
        settings.SALESFORCE_ARTICLE_BODY_FIELD: body,
    }
    result = kav_api.update(kav_id, data)
    if result != HTTPStatus.NO_CONTENT:
        msg = 'Error updating draft KnowledgeArticleVersion (ID={})'.format(
            kav_id,
        )
        raise KnowlegeError(msg)


def upload_draft(filename, sf):
    """Create a draft KnowledgeArticleVersion."""
    kav_api = getattr(sf, settings.SALESFORCE_ARTICLE_TYPE)
    with open(filename, 'r') as f:
        html = f.read()
    url_name, title, summary, body = parse(html)
    body = replace_image_links(body)

    # search for existing draft. if found, update fields and return
    result = query_kav(sf, url_name, 'draft')
    if result['totalSize'] == 1:  # cannot be > 1
        kav_id = result['records'][0]['id']
        update_draft(kav_api, kav_id, title, summary, body)
        return kav_id

    # no drafts found. search for published article
    result = query_kav(sf, url_name, 'online')
    if result['totalSize'] == 0:
        # new article
        data = {
            'UrlName': url_name,
            'Title': title,
            'Summary': summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: body,
        }
        result = kav_api.create(data=data)
        kav_id = result['id']
    elif result['totalSize'] == 1:
        # new draft of existing article
        record = result['records'][0]

        # check for changes in article fields
        if (
            title == record['Title'] and
            summary == record['Summary'] and
            body == record[settings.SALESFORCE_ARTICLE_BODY_FIELD]
        ):
            # no update
            return

        # create draft copy of published article
        url = (
            sf.base_url +
            'knowledgeManagement/articleVersions/masterVersions'
        )
        data = {'articleId': record['KnowledgeArticleId']}
        result = sf._call_salesforce('POST', url, json=data)
        if result.status_code != HTTPStatus.CREATED:
            msg = (
                'Error creating new draft for KnowlegeArticle (ID={})'
            ).format(record['KnowledgeArticleId'])
            raise KnowlegeError(msg)
        kav_id = result.json()['id']
        update_draft(kav_api, kav_id, title, summary, body)

    return kav_id


def handle_image(filename):
    """Save image file to image server."""
    basename = os.path.basename(filename)
    s3 = boto3.resource('s3')
    with TemporaryDirectory() as d:
        # try to download the image to see if it exists
        localname = os.path.join(d, basename)
        try:
            s3.meta.client.download_file(
                settings.AWS_STORAGE_BUCKET_NAME,
                basename,
                localname,
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                # upload new image
                upload_image(s3, filename, basename)
                return
            else:
                raise
        # image exists, see if it needs update
        if not filecmp.cmp(filename, localname):
            # files differ, update the image
            upload_image(s3, filename, basename)


def upload_image(s3, filename, key):
    """Upload image to S3."""
    with open(filename, 'rb') as f:
        s3.meta.client.put_object(
            ACL='public-read',
            Body=f,
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
        )
