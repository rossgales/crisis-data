# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-26 21:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0015_auto_20170926_2120'),
    ]

    operations = [
        migrations.AlterField(
            model_name='geopoint',
            name='event',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='geopoint', to='streamcollect.Event'),
        ),
        migrations.AlterField(
            model_name='keyword',
            name='event',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='keyword', to='streamcollect.Event'),
        ),
    ]
