import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.files import File
from django.core.mail import send_mail
from django_rq import job

from .exceptions import HtmlError
from .models import Article
from .models import EasyditaBundle
from .models import Image


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
                        defaults={'html': html},
                    )
                    if article.html_hash != hash(html):
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
def update_article(article_pk, easydita_bundle_pk):
    article = Article.objects.get(pk=article_pk)
    easydita_bundle = EasyditaBundle.objects.get(pk=easydita_bundle_pk)
    article.update()
    article.last_updated_by = easydita_bundle
    article.save()
