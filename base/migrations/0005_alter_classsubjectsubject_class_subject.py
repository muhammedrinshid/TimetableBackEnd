# Generated by Django 4.2.13 on 2024-08-02 10:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_alter_room_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classsubjectsubject',
            name='class_subject',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_subject_subjects', to='base.classsubject'),
        ),
    ]
