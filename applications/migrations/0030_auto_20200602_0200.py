# Generated by Django 2.2.10 on 2020-06-02 07:00

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0029_auto_20200328_1720'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='phone_number',
            field=models.CharField(default='(999) 999-9999', max_length=14, validators=[django.core.validators.RegexValidator(message='Phone number must be entered in the following format:                                                                 (999) 999-9999', regex='^\\(\\d{3}\\)\\s\\d{3}-\\d{4}')]),
        ),
    ]
