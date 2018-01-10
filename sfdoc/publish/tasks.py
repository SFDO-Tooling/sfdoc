import os
from tempfile import TemporaryDirectory
from urllib.parse import urljoin

from django.conf import settings
from django_rq import job
from simple_salesforce.exceptions import SalesforceGeneralError

from .exceptions import HtmlError
from .exceptions import KnowledgeError
from .models import EasyditaBundle
from .salesforce import get_salesforce_api
from .utils import get_site_url
from .utils import handle_image
from .utils import publish_kav
from .utils import scrub
from .utils import email
from .utils import upload_draft


@job
def process_easydita_bundle(easydita_bundle_pk, review=False):
    """
    Get the bundle from easyDITA and process the contents.
    There are 3 phases:
        1) Check all HTML files for issues
        2) Upload drafts and image files
        3) Publish drafts
    """
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    sf = get_salesforce_api(review)
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
                        scrub(html)
                    except (
                        HtmlError,
                        KnowledgeError,
                        SalesforceGeneralError,
                    ) as e:
                        msg = 'Error checking HTML file {}'.format(
                            filename_full,
                        )
                        email(msg, easydita_bundle, e)
                        raise

        # upload article drafts and images
        publish_queue = []
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                filename_full = os.path.join(dirpath, filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    try:
                        kav_id = upload_draft(filename_full, sf)
                    except (KnowledgeError, SalesforceGeneralError) as e:
                        msg = 'Error uploading draft for HTML file {}'.format(
                            filename_full,
                        )
                        email(msg, easydita_bundle, e)
                        raise
                    if kav_id:
                        publish_queue.append(kav_id)
                elif ext.lower() in settings.IMAGE_EXTENSIONS:
                    try:
                        handle_image(filename_full, review)
                    except ImageError as e:
                        msg = 'Error updating image file {}'.format(
                            filename_full,
                        )
                        email(msg, easydita_bundle, e)
                        raise

        # publish article drafts
        for kav_id in publish_queue:
            try:
                publish_kav(kav_id, sf)
            except (KnowledgeError, SalesforceGeneralError) as e:
                msg = (
                    'Error publishing draft KnowledgeArticleVersion (ID={})'
                ).format(kav_id)
                email(msg, easydita_bundle, e)
                raise

    msg = (
        'easyDITA bundle {} has been successfully processed and uploaded to '
    ).format(easydita_bundle.easydita_id)
    if review:
        production_url = urljoin(
            get_site_url(),
            'publish/production/{}/'.format(easydita_bundle.easydita_id),
        )
        msg += (
            'the review Salesforce org. After approving the changes in the '
            'review org, use the following link to upload to the production '
            'org.\n\n{}'
        ).format(production_url)
        easydita_bundle.complete_review = True
    else:
        msg += 'the production Salesforce org.'
        easydita_bundle.complete_production = True
    easydita_bundle.save()
    email(msg, easydita_bundle)

    return 'Processed easyDITA bundle {}'.format(easydita_bundle.easydita_id)
