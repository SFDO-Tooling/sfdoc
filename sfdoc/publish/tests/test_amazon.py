import responses
from test_plus.test import TestCase

from ..amazon import S3


class TestS3(TestCase):

    @responses.activate
    def test_init(self):
        s3 = S3()
