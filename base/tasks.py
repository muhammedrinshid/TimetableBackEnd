# base/tasks.py
from celery import shared_task
from django.utils import timezone

@shared_task
def save_timetable_task():
    # Your logic to save the timetable goes here
    print(f"Saving timetable at {timezone.now()}")
