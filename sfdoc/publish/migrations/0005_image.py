# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-17 23:52
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("publish", "0004_auto_20180116_0110"),
    ]

    operations = [
        migrations.CreateModel(
            name="Image",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filename", models.CharField(max_length=255, unique=True)),
                (
                    "easydita_bundle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="publish.EasyditaBundle",
                    ),
                ),
            ],
        ),
    ]
