from django.urls import path
from ..views import time_table_views
urlpatterns = [
    
                path('', time_table_views.run_module_view, name='generate-new-time-table'),

                path('check-class-subjects/', time_table_views.check_class_subjects, name='check_class_subjects'),


]