# Generated by Django 4.2.13 on 2024-07-31 14:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='occupied',
            field=models.BooleanField(default=False),
        ),
    ]
