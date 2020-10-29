from django.test import RequestFactory
from test_plus.test import TestCase

from ..forms import PublishToProductionForm


class TestPublishToProductionForm(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_approve(self):
        request = self.factory.post(
            "/bundles/1",
            {
                "choice": PublishToProductionForm.APPROVE,
                "confirm": True,
            },
        )
        form = PublishToProductionForm(request.POST)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.approved())

    def test_reject(self):
        request = self.factory.post(
            "/bundles/1",
            {
                "choice": PublishToProductionForm.REJECT,
                "confirm": True,
            },
        )
        form = PublishToProductionForm(request.POST)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.approved())
