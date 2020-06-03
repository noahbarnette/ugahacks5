# Generated by Django 2.2.10 on 2020-06-02 17:36

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sponsors', '0005_auto_20200523_1556'),
    ]

    operations = [
        migrations.AddField(
            model_name='sponsor',
            name='scanned_hackers',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
    ]
