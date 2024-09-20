# Generated by Django 4.2.13 on 2024-09-20 06:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_rename_alotted_teacher_lesson_allotted_teacher'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserConstraintSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_conflict', models.BooleanField(default=True, editable=False)),
                ('teacher_conflict', models.BooleanField(default=True, editable=False)),
                ('student_group_conflict', models.BooleanField(default=True, editable=False)),
                ('elective_group_timeslot', models.BooleanField(default=True)),
                ('ensure_teacher_assigned', models.BooleanField(default=True)),
                ('ensure_timeslot_assigned', models.BooleanField(default=True)),
                ('tutor_lesson_load', models.BooleanField(default=True)),
                ('daily_lesson_limit', models.BooleanField(default=True)),
                ('prefer_consistent_teacher_for_subject', models.BooleanField(default=True)),
                ('prefer_subject_once_per_day', models.BooleanField(default=True)),
                ('avoid_teacher_consecutive_periods_overlapping_class', models.BooleanField(default=True)),
                ('avoid_continuous_subjects', models.BooleanField(default=True)),
                ('avoid_continuous_teaching', models.BooleanField(default=True)),
                ('avoid_consecutive_elective_lessons', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='constraint_settings', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]