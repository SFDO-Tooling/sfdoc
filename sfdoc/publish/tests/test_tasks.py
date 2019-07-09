from test_plus.test import TestCase
from unittest import mock
from .factories import BundleFactory
from .. import tasks
from ..models import Bundle


class TestTasks(TestCase):
    def test_process_bundle_queues_simple_case(self):
        with mock.patch('sfdoc.publish.tasks.process_bundle.delay') as mock_method:
            bundle1 = BundleFactory(status=Bundle.STATUS_QUEUED)
            bundle2 = BundleFactory(status=Bundle.STATUS_QUEUED)
            bundle3 = BundleFactory(status=Bundle.STATUS_QUEUED)

            tasks.process_bundle_queues()
            call = mock.call
            mock_method.assert_has_calls([call(bundle1.pk), call(bundle2.pk), call(bundle3.pk)], any_order=True)
            [bundle1, bundle2, bundle3]  # unused vars. Shut up linter

    def test_process_bundle_queues_complex_case(self):
        with mock.patch('sfdoc.publish.tasks.process_bundle.delay') as mock_method:
            bundle1 = BundleFactory(status=Bundle.STATUS_QUEUED)
            bundle2 = BundleFactory(status=Bundle.STATUS_QUEUED)
            bundle3 = BundleFactory(status=Bundle.STATUS_QUEUED)
            bundle4 = BundleFactory(status=Bundle.STATUS_QUEUED, easydita_resource_id=bundle1.easydita_resource_id)
            bundle5 = BundleFactory(status=Bundle.STATUS_QUEUED, easydita_resource_id=bundle2.easydita_resource_id)
            bundle6 = BundleFactory(status=Bundle.STATUS_QUEUED, easydita_resource_id=bundle3.easydita_resource_id)

            tasks.process_bundle_queues()
            call = mock.call
            mock_method.assert_has_calls([call(bundle1.pk), call(bundle2.pk), call(bundle3.pk)], any_order=True)
            [bundle1, bundle2, bundle3, bundle4, bundle5, bundle6]  # unused vars. Shut up linter
