from http import HTTPStatus
from io import BytesIO
from urllib.parse import urlencode
from urllib.parse import urljoin
from zipfile import ZipFile

from django.conf import settings
import responses


def create_test_html(url_name, title, summary, body):
    """Create string of HTML to use for testing."""
    s = '''
    <html>
    <head>
      <meta name="UrlName" content="{}">
      <meta name="description" content="{}">
      <meta name="is-visible-in-csp" content="true">
      <meta name="is-visible-in-pkb" content="true">
      <meta name="is-visible-in-prm" content="true">
      <meta name="{}" content="123">
      <meta name="{}" content="456">
      <title>{}</title>
    </head>
    <body>
      <div class="{}">
        {}
      </div>
    </body>
    </html>
    '''.format(
        url_name,
        summary,
        settings.ARTICLE_AUTHOR,
        settings.ARTICLE_AUTHOR_OVERRIDE,
        title,
        settings.ARTICLE_BODY_CLASS,
        body,
    )
    return s


def gen_article(n):
    """Create article fields using a number."""
    return {
        'id': n,
        'filename': 'test{}.html'.format(n),
        'url_name': 'test-{}-url-name'.format(n),
        'title': 'Test {} Title'.format(n),
        'summary': 'Test {} Summary'.format(n),
        'body': (
            'Test article content\n<br/>\n'
            '<img src="../images/test-image.png"/>\n'
        ),
    }


def mock_create_article(instance_url, kav_id):
    url = '{}/services/data/v{}/sobjects/{}/'.format(
        instance_url,
        settings.SALESFORCE_API_VERSION,
        settings.SALESFORCE_ARTICLE_TYPE,
    )
    responses.add('POST', url=url, json={'id': kav_id})


def mock_create_draft(instance_url, ka_id, kav_id):
    url = (
        '{}/services/data/v{}'
        '/knowledgeManagement/articleVersions/masterVersions'
    ).format(
        instance_url,
        settings.SALESFORCE_API_VERSION,
    )
    responses.add(
        'POST',
        url=url,
        status=HTTPStatus.CREATED,
        json={'id': str(kav_id)},
    )


def mock_bundle_download(url, articles):
    """Mock the response from easyDITA to provide the bundle."""
    zip_buff = BytesIO()
    with ZipFile(zip_buff, mode='w') as f_zip:
        for a in articles:
            f_zip.writestr(a['filename'], create_test_html(
                a['url_name'],
                a['title'],
                a['summary'],
                a['body'],
            ))
    responses.add(
        'GET',
        url=url,
        body=zip_buff.getvalue(),
        content_type='application/zip',
    )


def mock_publish_draft(instance_url, kav_id):
    url = (
        '{}/services/data/v{}/knowledgeManagement/articleVersions' +
        '/masterVersions/{}'
    ).format(
        instance_url,
        settings.SALESFORCE_API_VERSION,
        kav_id,
    )
    responses.add('PATCH', url=url, status=HTTPStatus.NO_CONTENT)


def mock_query(
    instance_url,
    url_name,
    publish_status,
    fields=None,
    return_val=None,
):
    """Mock KAV query to Salesforce org."""
    if not fields:
        fields = ['Id']
    query_s = urlencode({
        'q': (
            "SELECT {} FROM {} WHERE UrlName='{}' "
            "AND PublishStatus='{}' AND language='en_US'"
        ).format(
            ','.join(fields),
            settings.SALESFORCE_ARTICLE_TYPE,
            url_name,
            publish_status,
        ),
    })
    url = '{}/services/data/v{}/query/?{}'.format(
        instance_url,
        settings.SALESFORCE_API_VERSION,
        query_s,
    )
    responses.add(
        'GET',
        url=url,
        match_querystring=True,
        json=return_val,
    )


def mock_update_draft(instance_url, kav_id):
    url = urljoin(instance_url, 'services/data/v{}/sobjects/{}/{}'.format(
        settings.SALESFORCE_API_VERSION,
        settings.SALESFORCE_ARTICLE_TYPE,
        kav_id,
    ))
    responses.add(
        'PATCH',
        url=url,
        status=HTTPStatus.NO_CONTENT,
    )
