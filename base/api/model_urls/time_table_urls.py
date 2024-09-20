from django.urls import path
from ..views import time_table_views
urlpatterns = [
    
                path('', time_table_views.run_module_view, name='generate-new-time-table'),
                path('timetables/<uuid:timetable_id>/', time_table_views.timetable_detail, name='timetable_detail'),

                path('timetables/', time_table_views.list_timetables, name='list_timetables'),

                path('check-class-subjects/', time_table_views.check_class_subjects, name='check_class_subjects'),

                path('set-default/<uuid:pk>/', time_table_views.set_default_timetable, name='set_default_timetable'),
                path('teacher-view-day/<str:day_of_week>/',time_table_views.get_teacher_single_day_timetable , name='day_timetable'),
                path('default-teacher-view-week/', time_table_views.get_whole_teacher_default_week_timetable, name='default_teachers_week_timetable'),
                path('teacher-view-week/<str:pk>', time_table_views.get_whole_teacher_week_timetable, name='teachers_week_timetable'),
                path('classroom-timetable-week/<str:pk>/', time_table_views.get_classroom_week_timetable, name='week_timetable_classroom'),
                path('teacher-timetable-week/<str:pk>/', time_table_views.get_teacher_week_timetable, name='week_timetable_teacher'),
                path('student-view-day/<str:day_of_week>/',time_table_views.get_student_single_day_timetable , name='student_day_timetable'),
                path('default-student-view-week/', time_table_views.get_whole_student_default_week_timetable, name='default_student_week_timetable'),
                path('student-view-week/<str:pk>', time_table_views.get_whole_student_week_timetable, name='student_week_timetable'),
]