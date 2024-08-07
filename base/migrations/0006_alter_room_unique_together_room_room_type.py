# Generated by Django 4.2.13 on 2024-08-06 06:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_alter_classsubjectsubject_class_subject'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='room',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='room',
            name='room_type',
            field=models.CharField(choices=[('CLASSROOM', 'Classroom'), ('OFFICE', 'Office'), ('COMPUTER_LAB', 'Computer Lab'), ('LECTURE_HALL', 'Lecture Hall'), ('CONFERENCE_ROOM', 'Conference Room'), ('LABORATORY', 'Laboratory'), ('STUDY_AREA', 'Study Area'), ('OTHER', 'Other')], default='CLASSROOM', editable=False, max_length=20),
        ),
    ]
