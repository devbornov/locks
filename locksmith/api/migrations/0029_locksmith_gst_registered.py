# Generated by Django 5.2 on 2025-05-23 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_booking_emergency'),
    ]

    operations = [
        migrations.AddField(
            model_name='locksmith',
            name='gst_registered',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
