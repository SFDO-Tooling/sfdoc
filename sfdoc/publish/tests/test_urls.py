from django.core.urlresolvers import resolve
from django.core.urlresolvers import reverse
from test_plus.test import TestCase


class TestPublishURLs(TestCase):
    """Test URL patterns for publish app."""

    def test_webhook_resolve(self):
        """/publish/webhook/ should resolve to publish:webhook."""
        self.assertEqual(
            resolve('/publish/webhook/').view_name,
            'publish:webhook',
        )

    def test_webhook_resolve_2(self):
        """/publish/webhook/ should resolve to publish:webhook."""
        self.assertEqual(
            resolve('/publish/webhook').view_name,
            'publish:webhook',
        )

    def test_webhook_reverse(self):
        """publish:webhook should reverse to /publish/webhook/."""
        self.assertEqual(
            reverse('publish:webhook'),
            '/publish/webhook',
        )
