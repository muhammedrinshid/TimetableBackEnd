from django.shortcuts import render
from .views.commen import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['school_name'] = user.school_name
        token['working_days'] = user.working_days  # Changed this line
        token['teaching_slots'] = user.teaching_slots
        token['school_id'] = user.school_id
        token['all_classes_subject_assigned_atleast_one_teacher'] = user.all_classes_subject_assigned_atleast_one_teacher
        token['all_classes_assigned_subjects'] = user.all_classes_assigned_subjects

        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer