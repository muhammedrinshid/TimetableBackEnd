from django.db import migrations

    # School-specific Fields
DAYS_OF_WEEK = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]
def transfer_academic_schedule_data(apps, schema_editor):
    # Get the model classes
    User = apps.get_model('base', 'User')  # Replace 'base' with your actual app name
    UserAcademicSchedule = apps.get_model('base', 'UserAcademicSchedule')
    DaySchedule = apps.get_model('base', 'DaySchedule')

    # Iterate through existing users
    for user in User.objects.all():
        # Create UserAcademicSchedule instance
        academic_schedule, created = UserAcademicSchedule.objects.get_or_create(
            user=user,
            defaults={
                'average_students_allowed': user.average_students_allowed_in_a_class,
                'period_name': user.period_name
            }
        )

        # Create DaySchedule instances for each working day
        for day_code, _ in DAYS_OF_WEEK:
            if day_code in user.working_days:
                DaySchedule.objects.create(
                    schedule=academic_schedule,
                    day=day_code,
                    teaching_slots=user.teaching_slots
                )

def reverse_migration(apps, schema_editor):
    # Optional: Define how to reverse the migration if needed
    UserAcademicSchedule = apps.get_model('base', 'UserAcademicSchedule')
    DaySchedule = apps.get_model('base', 'DaySchedule')
    
    UserAcademicSchedule.objects.all().delete()
    DaySchedule.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('base', '0007_useracademicschedule_dayschedule'),  # Replace with your actual previous migration
    ]

    operations = [
        migrations.RunPython(transfer_academic_schedule_data, reverse_migration),
    ]