from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import HtmlError


def parse_html(html):
    """Parse article fields from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    # URL name
    url_name_tag = soup.find(attrs={'name': 'UrlName'})
    if not url_name_tag:
        raise HtmlError('Article URL name not found')
    url_name = url_name_tag['content']

    # title
    if not soup.title:
        raise HtmlError('Article title not found')
    title = soup.title.string

    # summary
    summary_tag = soup.find(attrs={'name': 'description'})
    if not summary_tag:
        raise HtmlError('Article summary not found')
    summary = summary_tag['content']

    # body
    body_tag = soup.find('div', class_=settings.ARTICLE_BODY_CLASS)
    body = body_tag.prettify()

    return url_name, title, summary, body


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


def scrub_html(html):
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
