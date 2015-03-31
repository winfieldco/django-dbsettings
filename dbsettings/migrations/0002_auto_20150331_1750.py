# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbsettings', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='setting',
            name='value',
        ),
        migrations.AddField(
            model_name='setting',
            name='value_image',
            field=models.ImageField(max_length=512, null=True, upload_to=b'dbsettings/image/%Y/%m/%d', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='setting',
            name='value_text',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
