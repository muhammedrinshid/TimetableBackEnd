from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime

class Command(BaseCommand):
    help = 'Populate TimeTableDaySchedule for Timetables created before November 20.'

    def handle(self, *args, **kwargs):
        from base.models import  User  # Replace 'your_app' with the actual app name
        from base.time_table_models import  Timetable, TimeTableDaySchedule  # Replace 'your_app' with the actual app name

        # Define the cutoff date
        cutoff_date = make_aware(datetime(2024, 11, 20))

        # Get timetables created before the cutoff date
        timetables = Timetable.objects.filter(created__lt=cutoff_date)

        for timetable in timetables:
            # Get the user (school) and working days
            user = timetable.school  # Assuming school is a ForeignKey to User
            working_days = user.working_days  # Assuming this is the ArrayField with working days

            for day_code in working_days:
                # Create TimeTableDaySchedule for each working day
                TimeTableDaySchedule.objects.create(
                    table=timetable,
                    day=day_code,
                    teaching_slots=timetable.number_of_lessons
                )

        self.stdout.write(self.style.SUCCESS('TimeTableDaySchedules populated successfully!'))
