# Generated by Django 4.2.13 on 2024-12-04 06:11

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0002_alter_daytimetabledate_day_timetable"),
    ]

    operations = [
        migrations.AddField(
            model_name="useracademicschedule",
            name="academic_year_end",
            field=models.DateField(
                blank=True, help_text="End date of the academic year", null=True
            ),
        ),
        migrations.AddField(
            model_name="useracademicschedule",
            name="academic_year_start",
            field=models.DateField(
                blank=True, help_text="Start date of the academic year", null=True
            ),
        ),
        migrations.CreateModel(
            name="TeacherActivityLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("date", models.DateField()),
                ("period", models.IntegerField()),
                (
                    "activity_type",
                    models.CharField(
                        choices=[("leave", "Leave"), ("extra_load", "Extra Load")],
                        max_length=20,
                    ),
                ),
                ("remarks", models.TextField(blank=True, null=True)),
                (
                    "day_lesson",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activity_logs",
                        to="base.daylesson",
                    ),
                ),
                (
                    "primary_teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="base.teacher",
                    ),
                ),
                (
                    "substitute_teacher",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="substitute_activities",
                        to="base.teacher",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["date", "primary_teacher", "activity_type"],
                        name="base_teache_date_ffa4f5_idx",
                    )
                ],
                "unique_together": {("date", "period", "primary_teacher")},
            },
        ),
    ]