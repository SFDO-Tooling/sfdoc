# Generated by Django 2.2.1 on 2019-07-13 18:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publish', '0032_docset'),
    ]

    operations = [
        migrations.AddField(
            model_name='docset',
            name='index_article_ka_id',
            field=models.CharField(null=True, max_length=64),
        ),
        migrations.AddField(
            model_name='docset',
            name='index_article_url',
            field=models.CharField(null=True, max_length=255),
        ),
    ]
