import responses
from test_plus.test import TestCase

from ..models import EasyditaBundle
from ..tasks import process_easydita_bundle
from .utils import gen_zip_file


class TestEasyditaBundleProcessor(TestCase):

    def setUp(self):
        self.easydita_bundle_id = 1

    @responses.activate
    def test_easydita_bundle_processor(self):
        file_name = 'test.txt'
        file_contents = 'test file contents'
        easydita_bundle = EasyditaBundle(easydita_id=1)
        responses.add(
            'GET',
            url=easydita_bundle.url,
            body=gen_zip_file(file_name, file_contents),
            content_type='application/zip',
        )
        easydita_bundle.save()
        process_easydita_bundle(easydita_bundle.pk)
        self.assertEqual(len(responses.calls), 1)
