# Generated by Django 4.2.13 on 2024-12-10 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0004_alter_teacheractivitylog_day_lesson_period"),
    ]

    operations = [
        migrations.AlterField(
            model_name="period",
            name="end_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="period",
            name="start_time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
