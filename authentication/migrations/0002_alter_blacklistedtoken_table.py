# Generated by Django 5.0.2 on 2024-03-04 13:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='blacklistedtoken',
            table='blacklist_access_token',
        ),
    ]
