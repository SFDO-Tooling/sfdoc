import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django_rq import job
from simple_salesforce.exceptions import SalesforceGeneralError

from .amazon import S3
from .exceptions import HtmlError
from .exceptions import SalesforceError
from .models import Article
from .models import EasyditaBundle
from .salesforce import Salesforce
from .utils import scrub_html
from .utils import email


@job
def process_easydita_bundle(easydita_bundle_pk):
    """
    Get the bundle from easyDITA and process the contents.
    HTML files are checked for issues first, then uploaded as drafts.
    """
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    salesforce = Salesforce()
    with TemporaryDirectory() as d:
        easydita_bundle.download(d)

        # check all HTML files
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    filename_full = os.path.join(dirpath, filename)
                    with open(filename_full, 'r') as f:
                        html = f.read()
                    try:
                        scrub_html(html)
                    except (
                        HtmlError,
                        SalesforceError,
                        SalesforceGeneralError,
                    ) as e:
                        msg = 'Error checking HTML file {}'.format(
                            filename_full,
                        )
                        email(msg, easydita_bundle, e)
                        raise

        # upload article drafts and images
        s3 = S3(draft=True)
        publish_queue = []
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                filename_full = os.path.join(dirpath, filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    try:
                        with open(filename_full, 'r') as f:
                            html = f.read()
                        kav_id = salesforce.upload_draft(html)
                    except (SalesforceError, SalesforceGeneralError) as e:
                        msg = 'Error uploading draft for HTML file {}'.format(
                            filename_full,
                        )
                        email(msg, easydita_bundle, e)
                        raise
                    Article.objects.create(
                        easydita_bundle=easydita_bundle,
                        kav_id=kav_id,
                    )
                elif ext.lower() in settings.IMAGE_EXTENSIONS:
                    try:
                        result = s3.handle_image(filename_full)
                    except Exception as e:
                        msg = 'Error updating image file {}'.format(
                            filename_full,
                        )
                        email(msg, easydita_bundle, e)
                        raise
                    if result in ('created', 'updated'):
                        Image.objects.create(
                            easydita_bundle=easydita_bundle,
                            filename=filename,
                        )

    msg = 'Processed easyDITA bundle {}'.format(easydita_bundle.easydita_id)
    easydita_bundle.complete_draft = True
    easydita_bundle.save()
    email(msg, easydita_bundle)
    return msg


@job
def publish_drafts(easydita_bundle_pk):
    """Publish all drafts related to an easyDITA bundle."""
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    salesforce = Salesforce()
    s3 = S3(draft=False)
    for article in easydita_bundle.articles:
        try:
            salesforce.publish_draft(kav_id)
        except (SalesforceError, SalesforceGeneralError) as e:
            msg = (
                'Error publishing draft KnowledgeArticleVersion (ID={}). '
                'The publishing process has been aborted.'
            ).format(article.kav_id)
            email(msg, easydita_bundle, e)
            raise
    for image in easydita_bundle.images:
        s3.copy_to_production(image.filename)
    easydita_bundle.complete_publish = True
    easydita_bundle.save()
