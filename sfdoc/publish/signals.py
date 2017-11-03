from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import EasyditaBundle
from .tasks import process_easydita_bundle


@receiver(post_save, sender=EasyditaBundle)
def handle_easydita_bundle_create(sender, **kwargs):
    if kwargs['created']:
        process_easydita_bundle.delay(kwargs['instance'].pk)
