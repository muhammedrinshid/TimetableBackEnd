from django.core.management.base import BaseCommand
from base.models import UserConstraintSettings

class Command(BaseCommand):
    help = "Update avoid_elective_in_first_period for all users"

    def handle(self, *args, **kwargs):
        UserConstraintSettings.objects.update(avoid_elective_in_first_period=True)
        self.stdout.write(self.style.SUCCESS("Successfully updated all users"))
