from django.conf import settings
from django.core.management.base import BaseCommand

from sfdoc.publish.salesforce import get_salesforce_api


class Command(BaseCommand):
    help = 'Sync articles from Salesforce org to app database'

    def handle(self, *args, **options):
        sf = get_salesforce_api()
        result = sf.query_all(
            "SELECT Id,KnowledgeArticleId,Title,UrlName,{}".format(
                settings.SALESFORCE_ARTICLE_BODY_FIELD
            ) +
            " FROM KnowledgeArticleVersion" +
            " WHERE ArticleType = '{}'".format(
                settings.SALESFORCE_ARTICLE_TYPE
            ) +
            " AND PublishStatus = 'Online'"
        )
        for record in result['records']:
            Article.objects.update_or_create(
                salesforce_id=record['KnowledgeArticleId'],
                defaults={
                    'body': record[settings.SALESFORCE_ARTICLE_BODY_FIELD],
                    'title': record['Title'],
                    'url_name': record['UrlName'],
                },
            )
            self.stdout.write(self.style.SUCCESS(
                'Successfully synced article {} "{}"'.format(
                    record['KnowledgeArticleId'],
                    record['Title']
                )
            ))
