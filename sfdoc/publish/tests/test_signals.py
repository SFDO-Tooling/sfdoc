import responses
from test_plus.test import TestCase

from ..signals import handle_easydita_bundle_create
from ..models import EasyditaBundle


class TestEasyditaBundleCreateHandler(TestCase):

    @responses.activate
    def test_easydita_bundle_create_handler(self):
        easydita_bundle = EasyditaBundle(easydita_id=1)
        handle_easydita_bundle_create(
            EasyditaBundle,
            created=True,
            instance=easydita_bundle,
        )
