# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-17 13:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Mention',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mention', models.CharField(max_length=200, unique=True)),
                ('tweets', models.ManyToManyField(to='streamcollect.Tweet')),
            ],
        ),
    ]