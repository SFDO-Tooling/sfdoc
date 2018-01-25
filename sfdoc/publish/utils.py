from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import HtmlError


def parse_html(html):
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
