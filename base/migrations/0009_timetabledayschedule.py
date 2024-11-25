from django.db import migrations, models
import django.db.models.deletion

def populate_timetable_day_schedules(apps, schema_editor):
    Timetable = apps.get_model('base', 'Timetable')
    TimeTableDaySchedule = apps.get_model('base', 'TimeTableDaySchedule')
    User = apps.get_model('auth', 'User')  # Assuming User is from the default auth app

    for timetable in Timetable.objects.all():
        # Get the working days for the timetable's school (user)
        user = timetable.school  # The User associated with this timetable
        working_days = user.working_days  # Assuming this is the ArrayField with the list of working days
        
        # Create a TimeTableDaySchedule for each working day in working_days
        for day_code in working_days:
            # Create the TimeTableDaySchedule entry for the day
            TimeTableDaySchedule.objects.create(
                table=timetable,
                day=day_code,
                teaching_slots=timetable.number_of_lessons
            )

class Migration(migrations.Migration):

    dependencies = [
        ("base", "008_transfer_user_academic_schedule"),  # Ensure this is the previous migration
    ]

    operations = [
        # Create the TimeTableDaySchedule model first
        migrations.CreateModel(
            name="TimeTableDaySchedule",
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
                (
                    "day",
                    models.CharField(
                        choices=[  # You can keep the DayChoices here if needed
                            ("MON", "Monday"),
                            ("TUE", "Tuesday"),
                            ("WED", "Wednesday"),
                            ("THU", "Thursday"),
                            ("FRI", "Friday"),
                            ("SAT", "Saturday"),
                            ("SUN", "Sunday"),
                        ],
                        max_length=3,
                    ),
                ),
                ("teaching_slots", models.PositiveIntegerField(default=1)),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="day_schedules",
                        to="base.timetable",
                    ),
                ),
            ],
            options={
                "ordering": ["day"],
                "unique_together": {("table", "day")},
            },
        ),
        # Run the function to populate the table with data
        migrations.RunPython(populate_timetable_day_schedules),
    ]
