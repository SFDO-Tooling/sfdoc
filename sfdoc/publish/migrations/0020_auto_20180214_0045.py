# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from django.db import migrations


def set_resource_id(apps, schema_editor):
    EasyditaBundle = apps.get_model('publish', 'EasyditaBundle')
    for bundle in EasyditaBundle.objects.all():
        for webhook in bundle.webhooks.all():
            data = json.loads(webhook.body)
            bundle.easydita_resource_id = data['resource_id']
            break
        bundle.save()


class Migration(migrations.Migration):

    dependencies = [
        ('publish', '0019_easyditabundle_easydita_resource_id'),
    ]

    operations = [
        migrations.RunPython(set_resource_id),
    ]
