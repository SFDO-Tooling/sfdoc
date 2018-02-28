import json
import os
from urllib.parse import urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import HtmlError
from .utils import is_html
from .utils import is_url_whitelisted


class HTML:
    """Article HTML utility class."""

    def __init__(self, html):
        """Parse article fields from HTML."""
        soup = BeautifulSoup(html, 'html.parser')

        # meta (URL name, summary, visibility settings)
        for attr, tag_name, optional in (
            ('url_name', 'UrlName', False),
            ('summary', 'description', True),
            ('is_visible_in_csp', 'is-visible-in-csp', False),
            ('is_visible_in_pkb', 'is-visible-in-pkb', False),
            ('is_visible_in_prm', 'is-visible-in-prm', False),
            ('author', settings.ARTICLE_AUTHOR, False),
        ):
            tag = soup.find('meta', attrs={'name': tag_name})
            if optional and (not tag or not tag['content']):
                setattr(self, attr, '')
                continue
            if not tag:
                raise HtmlError('Meta tag name={} not found'.format(tag_name))
            elif not tag['content']:
                raise HtmlError('Meta tag name={} has no content'.format(
                    tag_name,
                ))
            setattr(self, attr, tag['content'])

        # author override (Salesforce org user ID)
        tag = soup.find(
            'meta',
            attrs={'name': settings.ARTICLE_AUTHOR_OVERRIDE},
        )
        self.author_override = tag['content'] if tag else ''

        # title
        if not soup.title:
            raise HtmlError('Article title not found')
        self.title = str(soup.title.string)

        # body
        body_tag = soup.find('div', class_=settings.ARTICLE_BODY_CLASS)
        if not body_tag:
            raise HtmlError('Body tag <div class={} ...> not found'.format(
                settings.ARTICLE_BODY_CLASS,
            ))
        body = body_tag.renderContents()
        soup_body = BeautifulSoup(body, 'html.parser')
        self.body = soup_body.prettify()

    def create_article_data(self):
        return {
            'UrlName': self.url_name,
            'Title': self.title,
            'Summary': self.summary,
            'IsVisibleInCsp': self.is_visible_in_csp,
            'IsVisibleInPkb': self.is_visible_in_pkb,
            'IsVisibleInPrm': self.is_visible_in_prm,
            settings.SALESFORCE_ARTICLE_BODY_FIELD: self.body,
            settings.SALESFORCE_ARTICLE_AUTHOR_FIELD: self.author,
            settings.SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD: self.author_override,
        }

    def get_image_paths(self):
        """Get paths to linked images."""
        image_paths = set([])
        soup = BeautifulSoup(self.body, 'html.parser')
        for img in soup('img'):
            image_paths.add(img['src'])
        return image_paths

    def scrub(self):
        """Scrub article body using whitelists for tags/attributes and links."""
        def scrub_tree(tree):
            for child in tree.children:
                if hasattr(child, 'contents'):
                    if child.name not in settings.WHITELIST_HTML:
                        raise HtmlError('Tag "{}" not in whitelist'.format(child.name))
                    for attr in child.attrs:
                        if attr not in settings.WHITELIST_HTML[child.name]:
                            raise HtmlError(('Tag "{}" attribute "{}" not in whitelist').format(child.name, attr))
                        if attr in ('href', 'src'):
                            if not is_url_whitelisted(child[attr]):
                                raise HtmlError('URL {} not whitelisted'.format(child[attr]))
                    scrub_tree(child)
        soup = BeautifulSoup(self.body, 'html.parser')
        scrub_tree(soup)

    def update_links_draft(self):
        """Update links to draft location."""
        soup = BeautifulSoup(self.body, 'html.parser')
        images_path = 'https://{}.s3.amazonaws.com/{}'.format(
            settings.AWS_S3_BUCKET,
            settings.S3_IMAGES_DRAFT_DIR,
        )
        for a in soup('a'):
            if 'href' in a.attrs:
                o = urlparse(a['href'])
                if o.scheme or not o.path or not is_html(o.path):
                    continue
                basename = os.path.basename(o.path)
                a['href'] = os.path.splitext(basename)[0]
                if o.fragment:
                    a['href'] += '#' + o.fragment
        for img in soup('img'):
            img['src'] = images_path + os.path.basename(img['src'])
        self.body = soup.prettify()

    @staticmethod
    def update_links_production(html):
        """Update links to production location."""
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup('img'):
            img['src'] = img['src'].replace(settings.S3_IMAGES_DRAFT_DIR, '')
        return soup.prettify()
