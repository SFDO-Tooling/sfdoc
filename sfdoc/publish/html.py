import os
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
                setattr(self, attr, None)
                continue
            if not tag:
                raise HtmlError('Meta tag name={} not found'.format(tag_name))
            elif not tag['content']:
                raise HtmlError('Meta tag name={} has no content'.format(
                    tag_name,
                ))
            setattr(self, attr, tag['content'])

        # convert some attributes to booleans
        for attr in (
            'is_visible_in_csp',
            'is_visible_in_pkb',
            'is_visible_in_prm',
        ):
            val = True if getattr(self, attr).lower() == 'true' else False
            setattr(self, attr, val)

        # author override (Salesforce org user ID)
        tag = soup.find(
            'meta',
            attrs={'name': settings.ARTICLE_AUTHOR_OVERRIDE},
        )
        self.author_override = tag['content'] if tag else None

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
        self.body = body_tag.renderContents().decode('utf-8')

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

    def same_as_record(self, record):
        """Compare this object with an article from a Salesforce query."""
        def same(item1, item2):
            if not item1 and not item2:
                return True
            else:
                return item1 == item2
        rc = same(
            self.author,
            record[settings.SALESFORCE_ARTICLE_AUTHOR_FIELD],
        )
        rc = rc and same(
            self.author_override,
            record[settings.SALESFORCE_ARTICLE_AUTHOR_OVERRIDE_FIELD],
        )
        rc = rc and same(
            self.is_visible_in_csp,
            record['IsVisibleInCsp'],
        )
        rc = rc and same(
            self.is_visible_in_pkb,
            record['IsVisibleInPkb'],
        )
        rc = rc and same(
            self.is_visible_in_prm,
            record['IsVisibleInPrm'],
        )
        rc = rc and same(
            self.title,
            record['Title'],
        )
        rc = rc and same(
            self.summary,
            record['Summary'],
        )
        rc = rc and same(
            self.update_links_production(self.body).strip(),
            record[settings.SALESFORCE_ARTICLE_BODY_FIELD].strip(),
        )
        return rc

    def scrub(self):
        """Scrub article body using whitelists for tags/attributes and links."""
        problems = []

        def scrub_tree(tree):
            for child in tree.children:
                if hasattr(child, 'contents'):
                    if child.name not in settings.WHITELIST_HTML:
                        problems.append('Tag "{}" not in whitelist'.format(child.name))
                    for attr in child.attrs:
                        if attr not in settings.WHITELIST_HTML[child.name]:
                            problems.append('Tag "{}" attribute "{}" not in whitelist'.format(child.name, attr))
                        if attr in ('href', 'src'):
                            if not is_url_whitelisted(child[attr]):
                                problems.append('URL {} not whitelisted'.format(child[attr]))
                    scrub_tree(child)
        soup = BeautifulSoup(self.body, 'html.parser')
        scrub_tree(soup)
        return problems

    def update_links_draft(self, base_url=''):
        """Update links to draft location."""
        soup = BeautifulSoup(self.body, 'html.parser')
        images_path = 'https://{}.s3.amazonaws.com/{}'.format(
            settings.AWS_S3_BUCKET,
            settings.AWS_S3_DRAFT_DIR,
        )

        article_link_count = 1

        for a in soup('a'):
            if 'href' in a.attrs:
                o = urlparse(a['href'])
                if o.scheme or not o.path or not is_html(o.path):
                    continue
                base_url_prefix = ''
                if article_link_count > settings.SALESFORCE_ARTICLE_LINK_LIMIT:
                    base_url_prefix = base_url
                a['href'] = self.update_href(o, base_url_prefix)
                article_link_count += 1
        for img in soup('img'):
            img['src'] = images_path + os.path.basename(img['src'])
        self.body = str(soup)

    def update_href(self, parsed_url, base_url):
        basename = os.path.basename(parsed_url.path)
        new_href = '{}{}{}'.format(
            base_url,
            settings.SALESFORCE_ARTICLE_URL_PATH_PREFIX,
            os.path.splitext(basename)[0]
            )

        if parsed_url.fragment:
            new_href += '#' + parsed_url.fragment

        return new_href

    @staticmethod
    def update_links_production(html):
        """Update links to production location."""
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup('img'):
            img['src'] = img['src'].replace(settings.AWS_S3_DRAFT_DIR, '')
        return str(soup)
