# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-31 21:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("publish", "0012_auto_20180131_2135"),
    ]

    operations = [
        migrations.AlterField(
            model_name="webhook",
            name="easydita_bundle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="webhooks",
                to="publish.EasyditaBundle",
            ),
        ),
    ]
