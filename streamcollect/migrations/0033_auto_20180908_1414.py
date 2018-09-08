# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-09-08 14:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0032_auto_20180901_1720'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tweet',
            old_name='coordinates_long',
            new_name='coordinates_lon',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='new_screen_name',
            new_name='old_screen_name',
        ),
        migrations.AddField(
            model_name='tweet',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tweet',
            name='is_deleted_observed',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='is_deleted_observed',
            field=models.DateTimeField(null=True),
        ),
    ]
