# Generated by Django 5.2 on 2025-05-29 07:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_booking_is_customer_confirmed_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='locksmith_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('DENIED', 'Denied')], default='PENDING', max_length=10),
        ),
    ]
