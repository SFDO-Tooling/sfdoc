from http import HTTPStatus
import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.files import File
from django.core.mail import send_mail
from django_rq import job

from .exceptions import HtmlError
from .exceptions import PublishError
from .models import Article
from .models import EasyditaBundle
from .models import Image
from .salesforce import get_salesforce_api


@job
def process_easydita_bundle(pk):
    easydita_bundle = EasyditaBundle.objects.get(pk=pk)
    with TemporaryDirectory() as d:
        easydita_bundle.download(d)
        # first pass - scrub HTML files
        # This needs to complete before any changes are made in Salesforce org
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    with open(os.path.join(dirpath, filename), 'r') as f:
                        html = f.read()
                    try:
                        Article.scrub(html)
                    except HtmlError as e:
                        mail_subject = 'Error processing easyDITA bundle {}'.format(
                            easydita_bundle.easydita_id,
                        )
                        mail_message = 'Found issues in HTML file {}:\n\n{}'.format(
                            os.path.join(dirpath, filename),
                            e,
                        )
                        mail_from = settings.FROM_EMAIL
                        mail_to = settings.TO_EMAILS
                        send_mail(
                            mail_subject,
                            mail_message,
                            mail_from,
                            mail_to,
                        )
                        raise(e)
        # second pass - upload articles and images
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if ext.lower() in settings.HTML_EXTENSIONS:
                    with open(os.path.join(dirpath, filename), 'r') as f:
                        html = f.read()
                    article, created = Article.objects.update_or_create(
                        url_name=Article.get_url_name(html),
                        defaults={'html_new': html},
                    )
                    if article.changed:
                        update_article.delay(article.pk, easydita_bundle.pk)
                elif ext.lower() in settings.IMAGE_EXTENSIONS:
                    with open(os.path.join(dirpath, filename), 'rb') as f:
                        image_file = File(f)
                    image, created = Image.objects.update_or_create(
                        image_hash=hash(image_file.read()),
                        defaults={'image_file': image_file},
                    )
    return 'Processed easyDITA bundle pk={}'.format(pk)


@job
def publish(easydita_bundle_pk):
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    # wait until all articles have been processed
    for article in easydita_bundle.article_set.all():
        if article.changed and not article.ready_to_publish:
            return
    # publish all article drafts
    sf = get_salesforce_api()
    for article in easydita_bundle.article_set.all():
        if not article.changed:
            continue
        url = (
            sf.base_url +
            'knowledgeManagement/articleVersions/masterVersions/{}'.format(
                article.salesforce_kav_id,
            )
        )
        data = {'publishStatus': 'online'}  # increment minor version
        result = sf._call_salesforce('PATCH', url, json=data)
        if result.status_code != HTTPStatus.NO_CONTENT:
            article.reset_fields()
            raise PublishError(
                'Failed to publish KnowledgeArticleVersion {}: {}'.format(
                    article.salesforce_kav_id,
                    result,
                )
            )
        # update article fields
        article.html = article.html_new
        article.html_hash = hash(article.html_new)
        article.title = article.title_new
        article.summary = article.summary_new
        article.body = article.body_new
        article.last_updated_by = easydita_bundle
        article.ready_to_publish = False
        article.save()


@job
def update_article(article_pk, easydita_bundle_pk):
    article = Article.objects.get(pk=article_pk)
    article.update()
    publish.delay(easydita_bundle_pk)
