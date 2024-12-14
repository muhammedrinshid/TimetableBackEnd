from django.urls import path
from ..views import teacher_activity_views
    
urlpatterns = [
    path('teacher-activity-summary/', teacher_activity_views.retrieve_teacher_activity_summary, name='teacher_activity_summary'),
]               

