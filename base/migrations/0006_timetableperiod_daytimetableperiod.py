# Generated by Django 4.2.13 on 2024-12-10 11:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0005_alter_period_end_time_alter_period_start_time"),
    ]

    operations = [
        migrations.CreateModel(
            name="TimeTablePeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("period_number", models.PositiveIntegerField()),
                ("start_time", models.TimeField(blank=True, null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                (
                    "day_schedule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="periods",
                        to="base.timetabledayschedule",
                    ),
                ),
            ],
            options={
                "ordering": ["period_number"],
                "unique_together": {("day_schedule", "period_number")},
            },
        ),
        migrations.CreateModel(
            name="DayTimeTablePeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("period_number", models.PositiveIntegerField()),
                ("start_time", models.TimeField(blank=True, null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                (
                    "day_timetable",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="periods",
                        to="base.daytimetable",
                    ),
                ),
            ],
            options={
                "ordering": ["period_number"],
                "unique_together": {("day_timetable", "period_number")},
            },
        ),
    ]
