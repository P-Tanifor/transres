# Generated by Django 3.2.12 on 2022-02-20 12:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0003_remove_loadedbusinfo_departure_time'),
    ]

    operations = [
        migrations.DeleteModel(
            name='LoadedBusInfoView',
        ),
    ]
