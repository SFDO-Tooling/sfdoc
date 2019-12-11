import json
import os
import re
import shutil
import urllib.request
from unittest import skipUnless
from unittest.mock import patch

from . import utils

import boto3
from django.conf import settings
from django.test import override_settings
from django.db import connection
from test_plus.test import TestCase
import responses
from simple_salesforce.exceptions import SalesforceResourceNotFound

from sfdoc.publish import tasks
from sfdoc.publish.models import Article, Webhook, Image
from sfdoc.publish.salesforce import SalesforceArticles
from sfdoc.users.models import User
from sfdoc.publish.exceptions import SfdocError

from . import fake_easydita

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
#  If you want it to mock EasyDITA (mostly for performance reasons)
#  you can set EASYDITA_USERNAME=mock
#
#   You also probably need to be on VPN to contact your Org.

TESTING_CACHE = "/tmp/sfdoc_testing_cache"
SHOULD_MOCK_EASYDITA = settings.EASYDITA_USERNAME == "mock"
if SHOULD_MOCK_EASYDITA:
    print("=== MOCKING EASYDITA BY USING LOCAL FILES ===")
else:
    print("=== Not mocking easyDITA ===")


def integration_test(cls):
    """Test marker for tests  to be skipped under normal test running conditions"""
    if SHOULD_MOCK_EASYDITA:
        for key in dir(cls):
            if key.startswith("test_"):
                decorated = responses.activate(getattr(cls, key))
                setattr(cls, key, decorated)
    return skipUnless(
        settings.RUN_INTEGRATION_TESTS, "run integration tests"
    )(cls)


class TstHelpers:  # named to avoid confusing pytest
    def __init__(self):
        super().__init__(self)
        self.checkTestEnvironment()

    def checkTestEnvironment(self):
        """Several checks of the intention of the end-user to really obliterate
           their org."""
        assert settings.RUN_INTEGRATION_TESTS
        assert "test_" in connection.settings_dict["NAME"]
        assert os.environ.get("OKAY_TO_DELETE_SALESFORCE_KNOWLEDGE_ARTICLES"), (
            "Running integration tests require destructive changes to your SF instance!\n"
            + "You must authorize those with the OKAY_TO_DELETE_SALESFORCE_KNOWLEDGE_ARTICLES envvar"
        )

    def clearSalesforceArticles(self):
        """Delete all knowledge articles"""
        self.salesforce = SalesforceArticles(SalesforceArticles.ALL_DOCSETS)
        all_articles = self.salesforce.get_articles("Online")
        sfapis = {}
        for article in all_articles:
            docset_id = article[self.salesforce.docset_relation][settings.SALESFORCE_DOCSET_ID_FIELD]
            sfapi = sfapis.get(docset_id) or sfapis.setdefault(docset_id, SalesforceArticles(docset_id))

            sfapi.archive(article["Id"])

        all_articles = self.salesforce.get_articles("Draft")
        for article in all_articles:
            self.salesforce.delete(article["Id"])

        raw_sf_docset_api = getattr(self.salesforce.api, settings.SALESFORCE_DOCSET_SOBJECT)
        for docset in self.salesforce.get_docsets():
            raw_sf_docset_api.delete(docset["Id"])

        assert not self.salesforce.get_articles("Online")
        assert not self.salesforce.get_articles("Draft")

    def clearLocalCache(self):
        """Delete things from the local cache"""
        if os.path.exists(TESTING_CACHE):
            shutil.rmtree(TESTING_CACHE)
        os.makedirs(TESTING_CACHE)

    @property
    def s3(self):
        if not getattr(self, "_s3", None):
            self._s3 = boto3.resource("s3")
        return self._s3

    def clearS3(self):
        """Delete all S3 keys"""
        self.bucket.objects.all().delete()

    def assertS3ObjectExists(self, keyname):
        objs = list(self.bucket.objects.filter(Prefix=keyname))
        self.assertEqual(len(objs), 1, repr(objs))
        self.assertEqual(objs[0].key, keyname)

    def assertS3ObjectDoesNotExist(self, keyname):
        objs = list(self.bucket.objects.filter(Prefix=keyname))
        self.assertEqual(len(objs), 0, repr(objs))

    def createWebhook(self, body):
        self.webhook = Webhook.objects.create(body=json.dumps(body))
        tasks.process_webhook(self.webhook.pk)
        self.webhook.refresh_from_db()
        return self.webhook.bundle

    def assertTitles(self, article_list, titles):
        if titles:
            assert isinstance(titles[0], str)
        self.assertEqual(sorted(self.article_titles(article_list)), sorted(titles))

    def assertUrlResolves(self, url):
        self.assertTrue(urllib.request.urlopen(url).read(), url)

    def article_titles(self, article_list):
        if len(article_list) == 0:
            return []
        if isinstance(article_list[0], str):
            return article_list
        if getattr(article_list[0], "title", None):
            return [article.title for article in article_list]
        else:
            return [article["Title"] for article in article_list]

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

    def assertImgUrlInArticle(self, article_name, status, filename):
        kav = self.get_article(article_name, status)
        self.assertIn(filename, kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])

        regexp = f"(https://.*/{filename})"
        matches = re.search(regexp, kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])
        assert matches and matches[0], (
            regexp,
            kav[settings.SALESFORCE_ARTICLE_BODY_FIELD],
        )

        # image should be reachable
        self.assertUrlResolves(matches[0])

    def assertNoImagesScheduledForDeletion(self):
        deleted_images_in_db = Image.objects.filter(status=Image.STATUS_DELETED)
        self.assertEqual(len(deleted_images_in_db), 0, deleted_images_in_db)

    def assertStringNotInArticles(self, verboten, status):
        for article in self.salesforce.get_articles(status):
            kav_api = getattr(self.salesforce.api, settings.SALESFORCE_ARTICLE_TYPE)
            kav = kav_api.get(article["Id"])
            body = kav[settings.SALESFORCE_ARTICLE_BODY_FIELD]
            self.assertNotIn(verboten, body)

    def debugMock(self):
        return utils.makeDebugTemporaryDirectoryMock(
            default_dir=TESTING_CACHE, parent_prefix=self._testMethodName
        )


class FakeQueue:
    def __init__(self):
        self.calls = []

    def enqueue_call(self, func, args, kwargs, **_irrelevant_queuing_junk):
        self.calls.append((func, args, kwargs))

    def pump(self):
        current_calls = self.calls
        self.calls = []
        for func, args, kwargs in current_calls:
            func(*args, **kwargs)


@integration_test
class SFDocTestIntegration(TestCase, TstHelpers):
    def setUp(self):
        """Create a superuser and clear s3 and Salesforce"""
        User.objects.create_superuser(
            "testuser",
            "testuser@test.com",
            password="password",
            is_staff=True,
            is_superuser=True,
        )

        self.bucket = self.s3.Bucket(settings.AWS_S3_BUCKET)
        self.clearSalesforceArticles()
        self.clearS3()
        self.clearLocalCache()

        if SHOULD_MOCK_EASYDITA:
            utils.mock_easydita()
        self.fake_queue = FakeQueue()
    
    def process_bundle_from_webhook(self, webhook):
        with patch("rq.queue.Queue.enqueue_call", self.fake_queue.enqueue_call):
            bundle = self.createWebhook(webhook)

            # creating a webhook should have queued a job to process all bundle queues
            assert (tasks.process_bundle_queues, (), {}) in self.fake_queue.calls

            # do it myself
            self.fake_queue.pump()

            self.fake_queue.pump()
            bundle.refresh_from_db()
            return bundle

    def test_remove_article(self):
        with self.debugMock() as mocktempdir:
            # 1. Import a bundle
            mocktempdir.set_subprefix("_scenario_1_")
            bundle_A_V1 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
            articles = Article.objects.filter(bundle=bundle_A_V1,
                                              status__in=(Article.STATUS_NEW))
            self.assertTitles(articles, fake_easydita.ditamap_A_titles)
            self.assertTitles(self.salesforce.get_articles("draft"),
                              fake_easydita.ditamap_A_titles)

            # 2. User publishes the first bundle.
            mocktempdir.set_subprefix("_scenario_2_")
            tasks.publish_drafts(bundle_A_V1.pk)  # simulate publish from UI
            self.assertTitles(self.salesforce.get_articles("online"),
                              fake_easydita.ditamap_A_titles)

            # 3. Now import a different bundle with our to-be-deleted file
            mocktempdir.set_subprefix("_scenario_3_")
            bundle_B = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_B)
            articles = Article.objects.filter(bundle=bundle_B,
                                              status__in=(Article.STATUS_NEW))
            self.assertTitles(articles, fake_easydita.ditamap_B_titles)
            self.assertTitles(self.salesforce.get_articles("draft"),
                              fake_easydita.ditamap_B_titles)

            # should be able to find the article we're going to delete later
            self.assertIn(
                "Article 2, Bundle B",
                self.article_titles(self.salesforce.get_articles("draft")),
            )

            # 4. Publish the second bundle.
            mocktempdir.set_subprefix("_scenario_4_")
            tasks.publish_drafts(bundle_B.pk)  # simulate publish from UI

            # 5. Import a bundle with a single missing article and check that it disappears as a draft
            mocktempdir.set_subprefix("_scenario_5_")
            bundle_B_V3 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_b_V3)

            deleted = Article.objects.filter(bundle=bundle_B_V3, status="D")

            self.assertTitles(deleted, ["Article 2, Bundle B"])

            articles = self.salesforce.get_articles("draft")
            assert "Product Documentation" in (article["Article_Type__c"] for article in articles)
            assert "End Users;IT/Developers;LGBTQIA+" in (article["Topics__c"] for article in articles)

            # 6. Publish the bundle and check that it disappears as public
            mocktempdir.set_subprefix("_scenario_6_")
            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles
                + fake_easydita.ditamap_B_titles
            )
            tasks.publish_drafts(bundle_B_V3.pk)  # simulate publish from UI
            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles
                + fake_easydita.ditamap_B_V3_titles
            )
            self.assertNotIn(
                "Article 2, Bundle B",
                self.article_titles(self.salesforce.get_articles("online")),
            )

            # 7. Import and publish a version of the the other bundle and ensure that the first draft doesn't reappear
            mocktempdir.set_subprefix("_scenario_7_")
            bundle_A_V2 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V2)
            tasks.publish_drafts(bundle_A_V2.pk)  # simulate publish from UI

            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_V2_titles
                + fake_easydita.ditamap_B_V3_titles
            )
            self.assertNotIn(
                "Article 2, Bundle B",
                self.article_titles(self.salesforce.get_articles("online")),
            )

    def test_two_bundles_and_missing_articles(self):
        with self.debugMock() as mocktempdir:
            mocktempdir.set_subprefix("_scenario_1_")
            assert os.path.exists(TESTING_CACHE)

            # 1. Import a bundle
            bundle_A_V1 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
            self.assertStringNotInArticles(settings.AWS_S3_PUBLIC_IMG_DIR, "DRAFT")
            assert os.path.exists(TESTING_CACHE)

            # Check that we imported articles into both local DB and SF Org
            # compare # of database models to draft articles
            sforg_article_list = self.salesforce.get_articles("draft")
            self.assertEqual(len(sforg_article_list), len(Article.objects.all()))
            self.assertTitles(
                sforg_article_list,
                fake_easydita.ditamap_A_titles,
            )

            # check that we created the right number of "NEW" status models in PG
            pg_models = Article.objects.filter(bundle=bundle_A_V1)
            self.assertEqual(len(sforg_article_list), len(pg_models))

            self.assertNoImagesScheduledForDeletion()

            # 2. Publish the first bundle. Check that the articles are published.
            mocktempdir.set_subprefix("_scenario_2_")
            tasks.publish_drafts(bundle_A_V1.pk)  # simulate publish from UI
            self.assertStringNotInArticles(settings.AWS_S3_DRAFT_IMG_DIR, "Online")
            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles,
            )
            self.assertNoImagesScheduledForDeletion()

            self.assertTitles([], self.salesforce.get_articles("draft"))

            # 3. Now import a different bundle. Check that the new articles
            #    are drafts and the old ones are still online.
            mocktempdir.set_subprefix("_scenario_3_")
            bundle_B = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_B)
            sforg_article_list = self.salesforce.get_articles("draft")

            # check that they were added to SF
            self.assertTitles(sforg_article_list, fake_easydita.ditamap_B_titles)

            # check that we created "NEW" status models in PG for all bundle_B
            # objects
            pg_models = Article.objects.filter(bundle=bundle_B, status="N")
            self.assertTitles(pg_models, fake_easydita.ditamap_B_titles)

            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles,
            )

            self.assertStringNotInArticles(settings.AWS_S3_DRAFT_IMG_DIR, "Draft")

            # check that no articles were deleted or changed.
            other_stuff = Article.objects.filter(bundle=bundle_B).exclude(status="N")
            assert not other_stuff
            self.assertNoImagesScheduledForDeletion()

            # 4. Publish the second bundle. Check that both sets of articles
            #    stay published.
            mocktempdir.set_subprefix("_scenario_4_")

            tasks.publish_drafts(bundle_B.pk)  # simulate publish from UI
            self.assertStringNotInArticles(settings.AWS_S3_DRAFT_IMG_DIR, "Online")

            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles
                + fake_easydita.ditamap_B_titles,
            )
            # no articles should still be in draft
            self.assertEqual(self.salesforce.get_articles("draft"), [])

    def test_changes(self):
        # 1. Import a bundle
        bundle_A_V1 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        self.assertStringNotInArticles(settings.AWS_S3_DRAFT_IMG_DIR, "Online")

        # 2. Publish the first bundle.
        tasks.publish_drafts(bundle_A_V1.pk)  # simulate publish from UI
        # 3. Now import a different bundle.
        bundle_B = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_B)
        # 4. Publish the second bundle.
        tasks.publish_drafts(bundle_B.pk)  # simulate publish from UI

        # 5.
        #    Change an article's title. Check that it updates.
        #    Change another article's summary. Check that it updates.
        #    Check that all articles from the second bundle are included still. (TBD)
        bundle_A_V2 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V2)
        self.assertIn(
            "Article A3! Updated",
            self.article_titles(self.salesforce.get_articles("draft")),
        )
        tasks.publish_drafts(bundle_A_V2.pk)  # simulate publish from UI
        self.assertIn(
            "Article A3! Updated",
            self.article_titles(self.salesforce.get_articles("online")),
        )

        kav = self.get_article("Article A2", "online")
        summary = kav["Summary"]
        # Updated article summary
        self.assertIn("This is a test article. Updated!", summary)

        public_articles = self.salesforce.get_articles("online")
        expected_articles = (
            fake_easydita.ditamap_A_V2_titles
            + fake_easydita.ditamap_B_titles
        )

        self.assertTitles(public_articles, expected_articles)
        self.assertNoImagesScheduledForDeletion()

    def test_images(self):
        # 1. Import a bundle
        bundle_A_V1 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        new_images = list(Image.objects.filter(status=Image.STATUS_NEW, bundle=bundle_A_V1))
        assert(len(new_images) == 3)
        assert not Image.objects.filter(status=Image.STATUS_CHANGED, bundle=bundle_A_V1)
        assert not Image.objects.filter(status=Image.STATUS_DELETED, bundle=bundle_A_V1)

        # 2. Publish the first bundle.
        tasks.publish_drafts(bundle_A_V1.pk)  # simulate publish from UI

        # 3. Add an image. Check that it ends up on S3.
        bundle_A_V3 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V3)
        testing_file = "Testing/Paul_test/bundleA/CategoryA/Article1/images/small.png"
        draft_img_s3_object = os.path.join(
            settings.AWS_S3_DRAFT_IMG_DIR, bundle_A_V3.docset_id + "/", testing_file
        )
        self.assertS3ObjectExists(draft_img_s3_object)
        new_images = list(Image.objects.filter(status=Image.STATUS_NEW, bundle=bundle_A_V3))
        assert(len(new_images) == 1)
        assert not Image.objects.filter(status=Image.STATUS_CHANGED)
        assert not Image.objects.filter(status=Image.STATUS_DELETED)

        self.assertImgUrlInArticle("Article A1", "draft", draft_img_s3_object)

        tasks.publish_drafts(bundle_A_V3.pk)  # simulate publish from UI

        # image should be on S3/drafts now
        # image should be on S3 / now
        public_img_s3_object = draft_img_s3_object.replace(
            settings.AWS_S3_DRAFT_IMG_DIR, settings.AWS_S3_PUBLIC_IMG_DIR
        )

        self.assertS3ObjectExists(public_img_s3_object)

        # image should be referred to in published version
        kav = self.get_article("Article A1", "online")
        self.assertImgUrlInArticle("Article A1", "online", public_img_s3_object)
        self.assertS3ObjectExists(public_img_s3_object)

        # 4. Remove an image. Checks that it disappears from HTML and S3.

        # we haven't deleted any images yet so the DB should have no records
        # of this type:
        deleted_images_in_db = Image.objects.filter(status=Image.STATUS_DELETED)
        self.assertEqual(len(deleted_images_in_db), 0)

        numdraftimages = len(
            list(self.bucket.objects.filter(Prefix=settings.AWS_S3_DRAFT_IMG_DIR))
        )
        self.assertTrue(numdraftimages, "Should be draft images!")
        numpubimages = len(
            list(self.bucket.objects.filter(Prefix=settings.AWS_S3_PUBLIC_IMG_DIR))
        )
        self.assertTrue(numpubimages, "Should be public images!")

        bundle_A_V4 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V4)
        kav = self.get_article("Article A1", "draft")

        # now we've deleted an image, so there should be 1 and only 1 such
        # record. This is the first one we have deleted
        self.assertEqual(Image.objects.filter(status=Image.STATUS_DELETED).count(), 1)
        self.assertEqual(Image.objects.filter(status=Image.STATUS_NEW, bundle=bundle_A_V4).count(), 0)
        self.assertEqual(Image.objects.filter(status=Image.STATUS_CHANGED, bundle=bundle_A_V4).count(), 0)

        # should be 1 less image on S3 drafts
        numdraftimages_now = len(
            list(self.bucket.objects.filter(Prefix=settings.AWS_S3_DRAFT_IMG_DIR))
        )
        self.assertEqual(numdraftimages_now, numdraftimages - 1)
        numpubimages_now = len(
            list(self.bucket.objects.filter(Prefix=settings.AWS_S3_PUBLIC_IMG_DIR))
        )
        self.assertEqual(numpubimages_now, numpubimages)

        self.assertNotIn("small.png", kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])
        self.assertS3ObjectDoesNotExist(draft_img_s3_object)

        tasks.publish_drafts(bundle_A_V4.pk)
        kav = self.get_article("Article A1", "online")
        self.assertNotIn("small.png", kav[settings.SALESFORCE_ARTICLE_BODY_FIELD])

        # should be 1 less public image on S3
        numpubimages_now = len(
            list(self.bucket.objects.filter(Prefix=settings.AWS_S3_PUBLIC_IMG_DIR))
        )
        self.assertEqual(numpubimages_now, numpubimages - 1)

        self.assertS3ObjectDoesNotExist(public_img_s3_object)

    def test_ensure_sf_docset_exists(self):
        uuid = "0000-0000-0000-0000"

        sf = SalesforceArticles(uuid)

        raw_sf_docset_api = getattr(sf.api, settings.SALESFORCE_DOCSET_SOBJECT)

        # first the docset should not exist at all. (or shouldn't after)
        try:
            result = raw_sf_docset_api.get_by_custom_id(
                settings.SALESFORCE_DOCSET_ID_FIELD, uuid
            )
            assert False, "Should not reach this line!"
        except SalesforceResourceNotFound:
            pass

        sf = SalesforceArticles(uuid)
        result = sf.sf_docset
        assert result[settings.SALESFORCE_DOCSET_STATUS_FIELD] == settings.SALESFORCE_DOCSET_STATUS_INACTIVE

        result2 = raw_sf_docset_api.get_by_custom_id(
            settings.SALESFORCE_DOCSET_ID_FIELD, uuid
        )
        assert sf.sf_docset["Id"] == result2["Id"]
        raw_sf_docset_api.delete(result["Id"])

    def test_docset_index_url_change(self):
        with self.debugMock() as mocktempdir:
            mocktempdir.set_subprefix("_scenario_10_")
            bundle_A_V1 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
            tasks.publish_drafts(bundle_A_V1.pk)  # simulate publish from UI

            docset = SalesforceArticles(bundle_A_V1.docset_id).sf_docset
            index_article_id = docset[settings.SALESFORCE_DOCSET_INDEX_REFERENCE_FIELD]
            index_article = self.salesforce.find_article_by_name("SFDO-BundleA-Documentation", "Online")
            assert index_article["KnowledgeArticleId"] == index_article_id

            mocktempdir.set_subprefix("_scenario_11_")
            # this new bundle has a different UrlName for the index article
            # so it should end up with a new ID
            # which should change the docset ("Hub_Product_Description__c") too
            bundle_A_V6 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V6)
            tasks.publish_drafts(bundle_A_V6.pk)  # simulate publish from UI

            docset = SalesforceArticles(bundle_A_V1.docset_id).sf_docset
            index_article_id2 = docset[settings.SALESFORCE_DOCSET_INDEX_REFERENCE_FIELD]
            assert index_article_id != index_article_id2
            new_index_article = self.salesforce.find_article_by_name("SFDO-BundleA-Documentation-URL2", "Online")
            assert new_index_article["KnowledgeArticleId"] == index_article_id2
            try:
                self.salesforce.find_article_by_name("SFDO-BundleA-Documentation", "Online")
                assert False, "Should not get to this line of code"
            except IndexError:
                pass  # we're good

    def test_two_bundles_interleaved(self):
        """Test two bundles being ready for review at the same time"""
        with self.debugMock() as mocktempdir:
            mocktempdir.set_subprefix("_scenario_1_")
            assert os.path.exists(TESTING_CACHE)

            # 1. Import a bundle
            bundle_A_V1 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
            assert bundle_A_V1.status == bundle_A_V1.STATUS_DRAFT

            self.assertStringNotInArticles(settings.AWS_S3_PUBLIC_IMG_DIR, "DRAFT")
            assert os.path.exists(TESTING_CACHE)

            # Check that we imported articles into both local DB and SF Org
            # compare # of database models to draft articles
            sforg_article_list = self.salesforce.get_articles("draft")
            self.assertEqual(len(sforg_article_list), len(Article.objects.all()))
            self.assertTitles(
                sforg_article_list,
                fake_easydita.ditamap_A_titles,
            )

            # check that we created the right number of "NEW" status models in PG
            pg_models = Article.objects.filter(bundle=bundle_A_V1)
            self.assertEqual(len(sforg_article_list), len(pg_models))

            self.assertNoImagesScheduledForDeletion()

            # 2. Now import a different bundle. Check that the new articles
            #    are drafts and the old ones are still draft also.
            mocktempdir.set_subprefix("_scenario_2_")
            bundle_B = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_B)
            sforg_article_list = self.salesforce.get_articles("draft")

            # check that they were added to SF
            self.assertTitles(sforg_article_list, fake_easydita.ditamap_A_titles +
                              fake_easydita.ditamap_B_titles)

            # check that we created "NEW" status models in PG for all bundle_B
            # objects
            pg_models = Article.objects.filter(bundle=bundle_B, status="N")
            self.assertTitles(pg_models, fake_easydita.ditamap_B_titles)

            # check that no articles were deleted or changed.
            other_stuff = Article.objects.filter(bundle=bundle_B).exclude(status="N")
            assert not other_stuff
            self.assertNoImagesScheduledForDeletion()

            # 3. Add another bundle "bundle_A" and ensure that it stays queued, not processing.
            bundle_A_V2 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V2)
            assert bundle_A_V2.status == bundle_A_V2.STATUS_QUEUED

            # 4. Publish the first bundle. Check that the articles are published.
            mocktempdir.set_subprefix("_scenario_4_")
            tasks.publish_drafts(bundle_A_V1.pk)  # simulate publish from UI
            self.assertStringNotInArticles(settings.AWS_S3_DRAFT_IMG_DIR, "Online")
            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles,
            )
            self.assertNoImagesScheduledForDeletion()

            # bundle B stuff should still be unpublished
            self.assertTitles(self.salesforce.get_articles("draft"), fake_easydita.ditamap_B_titles)

            # 5. Publish the second bundle. Check that both sets of articles
            #    stay published.
            mocktempdir.set_subprefix("_scenario_5_")

            tasks.publish_drafts(bundle_B.pk)  # simulate publish from UI
            self.assertStringNotInArticles(settings.AWS_S3_DRAFT_IMG_DIR, "Online")

            self.assertTitles(
                self.salesforce.get_articles("online"),
                fake_easydita.ditamap_A_titles
                + fake_easydita.ditamap_B_titles,
            )
            # no articles should still be in draft
            self.assertEqual(self.salesforce.get_articles("draft"), [])

    @override_settings(REPUBLISH_UNCHANGED_ARTICLES=False)
    def test_same_bundle_push_and_publish_twice(self):
        """You can't publish identical bundles back to back usually."""
        bundle_A = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        tasks.publish_drafts(bundle_A.pk)  # simulate publish from UI
        with self.assertRaises(SfdocError) as e:
            self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        
        assert str(e.exception) == 'No articles or images changed'

    @override_settings(REPUBLISH_UNCHANGED_ARTICLES=True)
    def test_same_bundle_force_republish(self):
        """Allow publishing identical bundle twice in a row if settings allow."""
        bundle_A = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        tasks.publish_drafts(bundle_A.pk)  # simulate publish from UI
        # if the setting did not do what it is supposed to do, the next line
        # would throw an exception, as it does in test_same_bundle_push_and_publish_twice
        bundle_A2 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        tasks.publish_drafts(bundle_A2.pk)  # simulate publish from UI

    def test_same_bundle_old_bundle(self):
        """Should be able to revert a publish"""
        bundle_A = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        tasks.publish_drafts(bundle_A.pk)  # simulate publish from UI
        bundle_A_V2 = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A_V2)
        tasks.publish_drafts(bundle_A_V2.pk)  # simulate publish from UI
        bundle_A = self.process_bundle_from_webhook(fake_easydita.fake_webhook_body_doc_A)
        tasks.publish_drafts(bundle_A.pk)  # simulate publish from UI
