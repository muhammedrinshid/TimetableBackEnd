from django.urls import path
from ..views import time_table_views
urlpatterns = [
    
                path('', time_table_views.run_module_view, name='generate-new-time-table'),
                path('timetables/<uuid:timetable_id>/', time_table_views.timetable_detail, name='timetable_detail'),

                path('timetables/', time_table_views.list_timetables, name='list_timetables'),

                path('check-class-subjects/', time_table_views.check_class_subjects, name='check_class_subjects'),

                path('set-default/<uuid:pk>/', time_table_views.set_default_timetable, name='set_default_timetable'),

]