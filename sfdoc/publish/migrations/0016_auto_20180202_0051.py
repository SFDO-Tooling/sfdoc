# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-02 00:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publish', '0015_auto_20180202_0044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='draft_preview_url',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='article',
            name='kav_id',
            field=models.CharField(max_length=18),
        ),
        migrations.AlterField(
            model_name='image',
            name='filename',
            field=models.CharField(max_length=255),
        ),
    ]
