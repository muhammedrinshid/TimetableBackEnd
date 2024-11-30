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
        token['total_weekly_teaching_slots'] = user.academic_schedule.total_weekly_teaching_slots  # Changed this line
        token['teaching_slots'] = user.teaching_slots
        token['school_id'] = user.school_id
        token['is_ready_for_timetable'] = user.is_ready_for_timetable
        token['profile_image'] = user.profile_image.url if user.profile_image else None

        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
