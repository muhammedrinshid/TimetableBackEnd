# Generated by Django 4.2.13 on 2024-11-18 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0003_classroom_unique_class_id_within_school"),
    ]

    operations = [
        migrations.AddField(
            model_name="userconstraintsettings",
            name="avoid_elective_in_first_period",
            field=models.BooleanField(default=True),
        ),
    ]
