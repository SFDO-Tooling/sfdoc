import json
import os
import re
import urllib.request
from unittest import skipUnless

import boto3
from django.conf import settings
from django.db import connection
from test_plus.test import TestCase

from sfdoc.publish import tasks
from sfdoc.publish.models import Article, Webhook
from sfdoc.publish.salesforce import Salesforce
from sfdoc.users.models import User

from . import fake_easydita

#
#  This file represents a sort of "life in the day" of the system.
#
#  It does not run by default with other other tests, because it is
#  DESTRUCTIVE. IT WILL DELETE KNOWLEDGE ARTICLES IN YOUR ORG.
#
#  It should therefore only be run against snapshot or scratch orgs.
#
#  If you do have such an empty org, you'll need to run this with the
#  following environment variables set:
#
#   DJANGO_SETTINGS_MODULE=config.settings.integration_test
#   OKAY_TO_DELETE_SALESFORCE_KNOWLEDGE_ARTICLES=True
#
#   You also probably need to be on VPN to contact your Org.


def integration_test(func):
    """Test marker for tests  to be skipped under normal test running conditions"""
    return skipUnless(
        getattr(settings, "RUN_INTEGRATION_TESTS", False), "run integration tests"
    )(func)


class SFDocTestIntegration(TestCase):
    def checkTestEnvironment():
        """Several checks of the intention of the end-user to really obliterate
           their org."""
        assert getattr(settings, "RUN_INTEGRATION_TESTS")
        assert "test_" in connection.settings_dict["NAME"]
        assert os.environ.get("OKAY_TO_DELETE_SALESFORCE_KNOWLEDGE_ARTICLES"), (
            "Running integration tests require destructive changes to your SF instance!\n"
            + "You must authorize those with the OKAY_TO_DELETE_SALESFORCE_KNOWLEDGE_ARTICLES envvar"
        )

    def setUp(self):
        """Create a superuser and clear s3 and Salesforce"""
        User.objects.create_superuser(
            "testuser",
            "testuser@test.com",
            password="password",
            is_staff=True,
            is_superuser=True,
        )
        self.clearSalesforce()
        self.clearS3()

    def clearSalesforce(self):
        """Delete all knowledge articles"""
        self.salesforce = Salesforce()
        all_articles = self.salesforce.get_articles("Online")
        for article in all_articles:
            self.salesforce.archive(article["KnowledgeArticleId"], article["Id"])

        all_articles = self.salesforce.get_articles("Draft")
        for article in all_articles:
            self.salesforce.delete(article["Id"])

    @property
    def s3(self):
        if not getattr(self, "_s3", None):
            self._s3 = boto3.resource("s3")
        return self._s3

    def clearS3(self):
        """Delete all S3 keys"""
        bucket = self.s3.Bucket(settings.AWS_S3_BUCKET)
        bucket.objects.filter().delete()

    def assertS3ObjectExists(self, keyname):
        bucket = self.s3.Bucket(settings.AWS_S3_BUCKET)
        objs = list(bucket.objects.filter(Prefix=keyname))
        self.assertEqual(len(objs), 1, repr(objs))
        self.assertEqual(objs[0].key, keyname)

    def createWebhook(self, body):
        self.webhook = Webhook.objects.create(body=json.dumps(body))
        tasks.process_webhook(self.webhook.pk)
        self.webhook.refresh_from_db()
        return self.webhook.bundle

    def assertTitles(self, article_list, titles):
        self.assertEqual(self.article_titles(article_list), sorted(titles))

    def assertUrlResolves(self, url):
        self.assertTrue(urllib.request.urlopen(url).read(), url)

    def article_titles(self, article_list):
        return sorted([article["Title"] for article in article_list])

    def get_article(self, article_name, status):
        kav_object = next(
            updated_article
            for updated_article in self.salesforce.get_articles(status)
            if updated_article["Title"] == article_name
        )
        assert kav_object, kav_object
        kav_id = kav_object["Id"]
        kav_api = getattr(self.salesforce.api, settings.SALESFORCE_ARTICLE_TYPE)
        kav = kav_api.get(kav_id)
        return kav

    @integration_test
    def test_respond_to_webhook(self):
        # 1. Import a bundle
        bundle_A_V1 = self.createWebhook(fake_easydita.fake_webhook_body_doc_A)
        tasks.process_bundle(bundle_A_V1.pk, False)

        # Check that we imported articles into both local DB and SF Org
        # compare # of database models to draft articles
        article_list = self.salesforce.get_articles("draft")
        self.assertEqual(len(article_list), len(Article.objects.all()))
        self.assertTitles(article_list, fake_easydita.ditamap_A_titles)

        # 2. Now import a different bundle. Check that the new articles
        #    and the old ones are both available.

        bundle_B = self.createWebhook(fake_easydita.fake_webhook_body_doc_B)
        tasks.process_bundle(bundle_B.pk, False)
        article_list = self.salesforce.get_articles("draft")

        self.assertTitles(
            article_list,
            fake_easydita.ditamap_A_titles + fake_easydita.ditamap_B_titles,
        )
        # number of models should match DB articles because nothing has been
        # imported twice yet.
        self.assertEqual(len(article_list), len(Article.objects.all()))

        # 3. Publish the first bundle. Check that the articles are published.
        tasks.publish_drafts(bundle_A_V1.pk)
        self.assertTitles(
            self.salesforce.get_articles("online"), fake_easydita.ditamap_A_titles
        )
        # other articles should still be in draft
        self.assertTitles(
            self.salesforce.get_articles("draft"), fake_easydita.ditamap_B_titles
        )

        # 4. Publish a second bundle. Check that both sets of articles
        #    stay published.
        tasks.publish_drafts(bundle_B.pk)
        self.assertTitles(
            self.salesforce.get_articles("online"),
            fake_easydita.ditamap_A_titles + fake_easydita.ditamap_B_titles,
        )
        # no articles should still be in draft
        self.assertEqual(self.salesforce.get_articles("draft"), [])

        # 5. Remove an article from the first bundle. Check that it disappears.
        #    Change another article's title. Check that it updates.
        #    Change another article's summary. Check that it updates.
        #    Check that all articles from the second bundle are included still. (TBD)
        bundle_A_V2 = self.createWebhook(fake_easydita.fake_webhook_body_doc_A_V2)
        tasks.process_bundle(bundle_A_V2.pk, False)
        self.assertIn(
            "Article A3! Updated", self.article_titles(self.salesforce.get_articles("draft"))
        )
        tasks.publish_drafts(bundle_A_V2.pk)
        self.assertIn(
            "Article A3! Updated", self.article_titles(self.salesforce.get_articles("online"))
        )

        kav = self.get_article("Article A2", "online")
        summary = kav["Summary"]
        # Updated article summary
        self.assertIn("This is a test article. Updated!", summary)

        # TODO: This is going to be broken until the new feature is implemented:
        # self.assertTitles(self.salesforce.get_articles("online"), ditamap_A_V2_titles + ditamap_B_titles)

        # 6. Add an image. Check that it ends up on S3.
        bundle_A_V3 = self.createWebhook(fake_easydita.fake_webhook_body_doc_A_V3)
        tasks.process_bundle(bundle_A_V3.pk, False)
        draft_filename = "draft/small.png"
        self.assertS3ObjectExists(draft_filename)

        # image should be referred to in draft
        kav = self.get_article("Article A1", "draft")
        regexp = f"(https://.*/{draft_filename})"
        matches = re.search(regexp, kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])
        assert matches and matches[0], (regexp, kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])

        # image should be reachable
        self.assertUrlResolves(matches[0])

        tasks.publish_drafts(bundle_A_V3.pk)

        # image should be on S3/drafts now
        # image should be on S3 / now
        self.assertS3ObjectExists("small.png")

        # image should be referred to in published version
        kav = self.get_article("Article A1", "online")
        self.assertIn("/small.png", kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])

        # 7. Remove an image. Checks that it disappears from S3.
        bundle_A_V4 = self.createWebhook(fake_easydita.fake_webhook_body_doc_A_V4)
        tasks.process_bundle(bundle_A_V4.pk, False)
        kav = self.get_article("Article A1", "draft")
        self.assertNotIn("small.png", kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])

        tasks.publish_drafts(bundle_A_V4.pk)
        kav = self.get_article("Article A1", "online")
        self.assertNotIn("small.png", kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])
