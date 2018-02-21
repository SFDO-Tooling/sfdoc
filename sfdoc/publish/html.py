import json
import os
from urllib.parse import urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import HtmlError
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
            image_path = img['src'].replace(
                settings.IMAGES_URL_PLACEHOLDER,
                '../images',
            )
            image_paths.add(image_path)
        return image_paths

    def update_image_links(self):
        """Replace the image URL placeholder."""
        images_path = 'https://{}.s3.amazonaws.com/{}'.format(
            settings.AWS_STORAGE_BUCKET_NAME,
            settings.S3_IMAGES_DRAFT_DIR,
        )
        soup = BeautifulSoup(self.body, 'html.parser')
        for img in soup('img'):
            img['src'] = img['src'].replace(
                settings.IMAGES_URL_PLACEHOLDER,
                images_path,
            )
        self.body = soup.prettify()


def get_links(path, print_json=False, body_only=True):
    """Find all the links (href, src) in all HTML files under the path."""
    def proc(tree, links):
        for child in tree.children:
            if not hasattr(child, 'contents'):
                continue
            for attr in child.attrs:
                if attr in ('href', 'src'):
                    if not urlparse(child[attr]).scheme:
                        # not an external link, implicitly whitelisted
                        continue
                    links.add(child[attr])
            proc(child, links)
    links = set([])
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if filename in settings.SKIP_FILES:
                continue
            name, ext = os.path.splitext(filename)
            if ext.lower() in settings.HTML_EXTENSIONS:
                filename_full = os.path.join(dirpath, filename)
                with open(filename_full, 'r') as f:
                    html = f.read()
                if body_only:
                    html = HTML(html)
                    html = html.body
                soup = BeautifulSoup(html, 'html.parser')
                proc(soup, links)
    if print_json:
        print(json.dumps(sorted(list(links)), indent=2))
    return links


def get_tags(path, print_json=False, body_only=True):
    """Find all HTML tags/attributes in all HTML files under the path."""
    def proc(tree, tags):
        for child in tree.children:
            if not hasattr(child, 'contents'):
                continue
            if child.name not in tags:
                tags[child.name] = set([])
            for attr in child.attrs:
                tags[child.name].add(attr)
            proc(child, tags)
    tags = {}
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if filename in settings.SKIP_FILES:
                continue
            name, ext = os.path.splitext(filename)
            if ext.lower() in settings.HTML_EXTENSIONS:
                filename_full = os.path.join(dirpath, filename)
                with open(filename_full, 'r') as f:
                    html = f.read()
                if body_only:
                    html = HTML(html)
                    html = html.body
                soup = BeautifulSoup(html, 'html.parser')
                proc(soup, tags)
    if print_json:
        tags_json = {}
        for tag in sorted(tags.keys()):
            tags_json[tag] = []
            for item in sorted(list(tags[tag])):
                tags_json[tag].append(item)
        print(json.dumps(tags_json, indent=2))
    return tags


def scrub_html(html_raw):
    """Scrub article body using whitelists for tags/attributes and links."""
    html = HTML(html_raw)
    soup = BeautifulSoup(html.body, 'html.parser')

    def scrub_tree(tree):
        for child in tree.children:
            if hasattr(child, 'contents'):
                if child.name not in settings.HTML_WHITELIST:
                    raise HtmlError('Tag "{}" not in whitelist'.format(
                        child.name,
                    ))
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
    soup = BeautifulSoup(html, 'html.parser')
    for img in soup('img'):
        img['src'] = img['src'].replace(settings.S3_IMAGES_DRAFT_DIR, '')
    return soup.prettify()
