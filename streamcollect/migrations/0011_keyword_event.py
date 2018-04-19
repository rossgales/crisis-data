# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-26 17:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0010_auto_20170926_1704'),
    ]

    operations = [
        migrations.AddField(
            model_name='keyword',
            name='event',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='keyword', to='streamcollect.Event'),
            preserve_default=False,
        ),
    ]