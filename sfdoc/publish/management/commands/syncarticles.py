from django.conf import settings
from django.core.management.base import BaseCommand

from sfdoc.publish.models import Article
from sfdoc.publish.salesforce import get_salesforce_api


class Command(BaseCommand):
    help = 'Sync articles from Salesforce org to app database'

    def handle(self, *args, **options):
        sf = get_salesforce_api()
        result = sf.query_all(
            "SELECT KnowledgeArticleId,UrlName,Title,Summary,{}".format(
                settings.SALESFORCE_ARTICLE_BODY_FIELD
            ) +
            " FROM {}".format(settings.SALESFORCE_ARTICLE_TYPE) +
            " WHERE PublishStatus='Online' AND language='en_US'"
        )
        for record in result['records']:
            article, created = Article.objects.update_or_create(
                salesforce_id=record['KnowledgeArticleId'],
                defaults={
                    'url_name': record['UrlName'],
                    'title': record['Title'],
                    'summary': record['Summary'],
                    'body': record[settings.SALESFORCE_ARTICLE_BODY_FIELD],
                },
            )
            self.stdout.write(self.style.SUCCESS(
                'Successfully synced article {} "{}"'.format(
                    article.salesforce_id,
                    article.title,
                )
            ))
