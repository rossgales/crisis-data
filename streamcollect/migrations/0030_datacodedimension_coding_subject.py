# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-07-31 18:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0029_auto_20180731_1706'),
    ]

    operations = [
        migrations.AddField(
            model_name='datacodedimension',
            name='coding_subject',
            field=models.CharField(default='tweet', max_length=20),
            preserve_default=False,
        ),
    ]
