# Generated by Django 4.2.13 on 2024-09-07 06:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_alter_room_room_number_alter_room_unique_together'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lesson',
            old_name='alotted_teacher',
            new_name='allotted_teacher',
        ),
    ]