from django.urls import path
from ..views import analytics_views
urlpatterns = [
    
 path('teacher-utilization/<uuid:pk>/', analytics_views.teacher_utilization_view,    name='teacher-utilization') ,    
  path('teacher-utilization/', analytics_views.teacher_utilization_view,    name='teacher-utilization') ,      
  
]