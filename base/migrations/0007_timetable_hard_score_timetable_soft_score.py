# Generated by Django 4.2.13 on 2024-09-21 07:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_userconstraintsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetable',
            name='hard_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='timetable',
            name='soft_score',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]