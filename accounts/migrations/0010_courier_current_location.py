# Generated by Django 5.0.7 on 2025-02-12 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_deliveryfee_remove_payment_courier_courier_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='courier',
            name='current_location',
            field=models.CharField(blank=True, default='Processing Center', help_text='Enter the current country or city of the package', max_length=100, null=True),
        ),
    ]
