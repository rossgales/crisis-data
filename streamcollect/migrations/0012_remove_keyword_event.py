# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-26 17:26
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0011_keyword_event'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='keyword',
            name='event',
        ),
    ]
