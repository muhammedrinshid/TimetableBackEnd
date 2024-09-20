from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from base.models import UserConstraintSettings

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates UserConstraintSettings for all users who do not have one'

    def handle(self, *args, **kwargs):
        users_without_settings = User.objects.filter(constraint_settings__isnull=True)
        settings_created = 0

        for user in users_without_settings:
            UserConstraintSettings.objects.create(user=user)
            settings_created += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {settings_created} UserConstraintSettings')
        )