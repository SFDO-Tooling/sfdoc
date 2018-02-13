import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import HtmlError
from .utils import is_url_whitelisted

logger = logging.getLogger(__name__)


class HTML:
    """Article HTML utility class."""

    def __init__(self, html):
        """Parse article fields from HTML."""
        logger.info('Parsing article fields from HTML')
        soup = BeautifulSoup(html, 'html.parser')

        # meta (URL name, summary, visibility settings)
        for attr, tag_name, optional in (
            ('url_name', 'UrlName', False),
            ('summary', 'description', True),
            ('is_visible_in_app', 'is-visible-in-app', False),
            ('is_visible_in_csp', 'is-visible-in-csp', False),
            ('is_visible_in_pkb', 'is-visible-in-pkb', False),
            ('is_visible_in_prm', 'is-visible-in-prm', False),
        ):
            tag = soup.find('meta', attrs={'name': tag_name})
            if not tag:
                if optional:
                    setattr(self, attr, '')
                    continue
                raise HtmlError('Meta tag name={} not found'.format(tag_name))
            setattr(self, attr, tag['content'])

        # title
        if not soup.title:
            raise HtmlError('Article title not found')
        self.title = soup.title.string

        # body
        body_tag = soup.find('div', class_=settings.ARTICLE_BODY_CLASS)
        if not body_tag:
            raise HtmlError('Body tag class={} not found'.format(settings.ARTICLE_BODY_CLASS))
        self.body = body_tag.prettify()

    def update_image_links(self):
        """Replace the image URL placeholder."""
        logger.info('Updating image links to point at draft images')
        images_path = urljoin(
            settings.AWS_S3_URL,
            settings.AWS_STORAGE_BUCKET_NAME,
        )
        soup = BeautifulSoup(self.body, 'html.parser')
        for img in soup('img'):
            img['src'] = img['src'].replace(
                settings.IMAGES_URL_PLACEHOLDER,
                images_path,
            )
        self.body = soup.prettify()


def get_links(path):
    """Find all the links (href, src) in all HTML files under the path."""
    def proc(tree, links):
        for child in tree.children:
            if not hasattr(child, 'contents'):
                continue
            for attr in child.attrs:
                if attr in ('href', 'src'):
                    links.add(child[attr])
            proc(child, links)
    links = set([])
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            name, ext = os.path.splitext(filename)
            if ext.lower() in settings.HTML_EXTENSIONS:
                filename_full = os.path.join(dirpath, filename)
                with open(filename_full, 'r') as f:
                    html = f.read()
                soup = BeautifulSoup(html, 'html.parser')
                proc(soup, links)
    return links


def scrub_html(html):
    """Scrub HTML using whitelists for tags/attributes and links."""
    logger.info('Scrubbing HTML')
    soup = BeautifulSoup(html, 'html.parser')

    def scrub_tree(tree):
        for child in tree.children:
            if hasattr(child, 'contents'):
                if child.name not in settings.HTML_WHITELIST:
                    raise HtmlError('Tag "{}" not in whitelist'.format(child.name))
                for attr in child.attrs:
                    if attr not in settings.HTML_WHITELIST[child.name]:
                        raise HtmlError((
                            'Tag "{}" attribute "{}" not in whitelist'
                        ).format(child.name, attr))
                    if attr in ('href', 'src'):
                        if not is_url_whitelisted(child[attr]):
                            raise HtmlError('URL {} not whitelisted'.format(
                                child[attr],
                            ))
                scrub_tree(child)
    scrub_tree(soup)


def update_image_links_production(html):
    """Update image links to point at production images."""
    logger.info('Updating image links to point at production images')
    soup = BeautifulSoup(html, 'html.parser')
    for img in soup('img'):
        img['src'] = img['src'].replace(settings.S3_IMAGES_DRAFT_DIR, '')
    return soup.prettify()
