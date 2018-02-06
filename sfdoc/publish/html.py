from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import HtmlError


class HTML:
    """Article HTML utility class."""

    def __init__(self, html):
        """Parse article fields from HTML."""
        soup = BeautifulSoup(html, 'html.parser')

        # meta (URL name, summary, visibility settings)
        for attr, tag_name in (
            ('url_name', 'UrlName'),
            ('summary', 'description'),
            ('is_visible_in_app', 'is-visible-in-app'),
            ('is_visible_in_csp', 'is-visible-in-csp'),
            ('is_visible_in_pkb', 'is-visible-in-pkb'),
            ('is_visible_in_prm', 'is-visible-in-prm'),
        ):
            tag = soup.find('meta', attrs={'name': tag_name})
            if not tag:
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
