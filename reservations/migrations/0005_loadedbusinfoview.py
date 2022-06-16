# Generated by Django 3.2.12 on 2022-02-20 12:53

from django.db import migrations, models
import django.db.models.deletion
import django.views.generic.base


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0004_delete_loadedbusinfoview'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoadedBusInfoView',
            fields=[
                ('passengerbookings_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='reservations.passengerbookings')),
            ],
            bases=('reservations.passengerbookings', django.views.generic.base.View),
        ),
    ]