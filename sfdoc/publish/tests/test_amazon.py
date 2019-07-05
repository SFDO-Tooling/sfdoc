import responses
from test_plus.test import TestCase

from ..amazon import S3
from .factories import BundleFactory


class TestS3(TestCase):

    @responses.activate
    def test_init(self):
        bundle = BundleFactory()
        S3(bundle)
