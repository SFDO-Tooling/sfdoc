from http import HTTPStatus

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files import File
from django.core.mail import send_mail

from .exceptions import HtmlError
from .exceptions import KnowledgeError
from .models import Image


def check_html(filename, sf):
    """
    Check HTML using tag/attribute whitelist and ensure there are no existing
    drafts with the same URL name.
    """
    with open(filename, 'r') as f:
        html = f.read()
    # scrub HTML using tag/attr whitelist
    scrub(html)
    # parse article fields from HTML
    url_name, title, summary, body = parse(html)
    # search for existing drafts
    query_str = (
        "SELECT Id FROM {} WHERE UrlName='{}' "
        "AND PublishStatus='draft' AND language='en_US'"
    ).format(settings.SALESFORCE_ARTICLE_TYPE, url_name)
    result = sf.query(query_str)
    if result['totalSize'] > 0:
        msg = (
            'Found draft article with URL name "{}" (ID={}). '
            'Publish or delete this draft and try again.'
        ).format(url_name, result['records'][0]['id'])
        raise KnowledgeError(msg)


def mail_error(message, e, easydita_bundle):
    """Send email on error."""
    subject = '[sfdoc] Error processing easyDITA bundle {}'.format(
        easydita_bundle.easydita_id,
    )
    message += (
        '\n\nError class: {}\nError info: {}\n\neasyDITA bundle URL: {}\n'
    ).format(e.__class__.__name__, e, easydita_bundle.url)
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


def replace_image_links(html_body):
    """Replace the image URL placeholder."""
    soup = BeautifulSoup(html_body, 'html.parser')
    for img in soup('img'):
        img['src'] = img['src'].replace(
            settings.IMAGES_URL_PLACEHOLDER,
            settings.IMAGES_URL_ROOT,
        )
    return soup.prettify()


def scrub(html):
    """Scrub the HTML file for security."""
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


def upload_draft(filename, sf):
    """Create a draft KnowledgeArticleVersion."""
    with open(filename, 'r') as f:
        html = f.read()
    url_name, title, summary, body = parse(html)
    body = replace_image_links(body)
    query_str = (
        "SELECT Id,KnowledgeArticleId,Title,Summary,{} FROM {} "
        "WHERE UrlName='{}' AND PublishStatus='online' AND language='en_US'"
    ).format(
        settings.SALESFORCE_ARTICLE_BODY_FIELD,
        settings.SALESFORCE_ARTICLE_TYPE,
        url_name,
    )
    result = sf.query(query_str)
    kav_api = getattr(sf, settings.SALESFORCE_ARTICLE_TYPE)
    if result['totalSize'] == 0:
        # new URL name --> new article
        data = {
            'UrlName': url_name,
            'Title': title,
            'Summary': summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: body,
        }
        result = kav_api.create(data=data)
        kav_id = result['id']
    elif result['totalSize'] == 1:
        # existing URL name --> new version of existing article
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

        # update draft fields
        data = {
            'Title': title,
            'Summary': summary,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: body,
        }
        result = kav_api.update(kav_id, data)
        if result != HTTPStatus.NO_CONTENT:
            msg = 'Error updating KnowledgeArticleVersion (ID={})'.format(
                kav_id,
            )
            raise KnowlegeError(msg)

    return kav_id


def upload_image(filename):
    """Save image file to image server."""
    with open(filename, 'rb') as f:
        image_file = File(f)
    Image.objects.update_or_create(
        image_hash=hash(image_file.read()),
        defaults={'image_file': image_file},
    )
