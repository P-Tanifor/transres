# Generated by Django 3.2.12 on 2022-02-16 16:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_loadedbusinfo_loadedbusinfoview'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='loadedbusinfo',
            name='departure_time',
        ),
    ]
