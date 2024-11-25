from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserAcademicSchedule, UserConstraintSettings
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_related_models(sender, instance, created, **kwargs):
    print("hi ima going to creating ")

    if created:
        print("hi created ")
        UserAcademicSchedule.objects.create(user=instance)
        UserConstraintSettings.objects.create(user=instance)
