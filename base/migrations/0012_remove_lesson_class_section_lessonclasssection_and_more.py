# Generated by Django 4.2.13 on 2024-08-14 12:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0011_alter_timetable_feasible_alter_timetable_optimal'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lesson',
            name='class_section',
        ),
        migrations.CreateModel(
            name='LessonClassSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_of_students', models.IntegerField()),
                ('class_section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.classsection')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.lesson')),
            ],
        ),
        migrations.AddField(
            model_name='lesson',
            name='class_sections',
            field=models.ManyToManyField(related_name='lessons', through='base.LessonClassSection', to='base.classsection'),
        ),
    ]
