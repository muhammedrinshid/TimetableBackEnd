# Generated by Django 4.2.13 on 2024-08-19 13:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsubjectsubject',
            name='preferred_rooms',
            field=models.ManyToManyField(related_name='class_subject_subjects', to='base.room'),
        ),
    ]
