# Generated by Django 5.2 on 2025-05-19 05:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_alter_adminservice_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='emergency',
            field=models.BooleanField(default=False, help_text='Is this an emergency service?'),
        ),
    ]
