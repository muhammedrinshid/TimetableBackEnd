from django.urls import path
from ..views import time_table_views ,day_timetable_views,download_timetable_files_views


urlpatterns = [
    # Trigger to initiate the scheduling of a new timetable
    # The 'seconds' parameter allows setting a delay before scheduling begins
    path('build-timetable/<int:seconds>/', time_table_views.run_module_view, name='generate_new_timetable'),

    # Verification to check if the user is eligible to create a new timetable
    path('check-class-subjects/', time_table_views.check_class_subjects, name='check_class_subjects'),

    # Manage timetables
    # - List all timetables for the user
    # - View, update, and delete a specific timetable by its unique UUID
    # - Set a specified timetable as the default timetable
    path('timetables/', time_table_views.list_timetables, name='list_timetables'),
    path('timetables/<uuid:timetable_id>/', time_table_views.timetable_detail, name='timetable_detail'),
    path('set-default/<uuid:pk>/', time_table_views.set_default_timetable, name='set_default_timetable'),

    # Single Day Timetable View (for teachers and students)
    # - Retrieve the full timetable for a single day, specific to either teachers or students
    # - 'day_of_week' parameter specifies the day to view
    path('teacher-view-day/<str:date_str>/', day_timetable_views.get_whole_teacher_single_day_timetable, name='teacher_day_timetable'),
    path('student-view-day/<str:date_str>/', day_timetable_views.get_whole_student_single_day_timetable, name='student_day_timetable'),

    # Default Weekly Timetable View (for teachers and students)
    # - Retrieve the entire weekly timetable of the default timetable, specific to either teachers or students
    path('default-teacher-view-week/', time_table_views.fetch_all_teachers_weekly_timetable, name='default_teachers_week_timetable'),

    path('default-student-condensed-view-week/',  time_table_views.default_student_week_timetable_condensed_view,   name='default-student-condensed-timetable'),

    path('default-student-view-week/', time_table_views.fetch_all_students_weekly_timetable, name='default_students_week_timetable'),

    # Weekly Timetable for Editing (for teachers and students)
    # - Fetch the entire weekly timetable for editing purposes
    # - Separate view for submitting edited timetable for students
    path('edit-teacher-week-timetable/<str:pk>/', time_table_views.fetch_all_teachers_weekly_timetable, name='teacher_week_timetable_for_edit'),
    path('edit-student-week-timetable/<str:pk>/', time_table_views.fetch_all_students_weekly_timetable, name='student_week_timetable_for_edit'),
    # Submit edited student timetable
    path('submit-edit-student-week-timetable/<str:pk>/', time_table_views.submit_student_week_timetable_edits, name='submit_student_week_timetable_edits'),
    # Submit edited student timetable

    path('submit-edit-teacher-week-timetable/<str:pk>/', time_table_views.submit_teacher_week_timetable_edits, name='submit_teacher_week_timetable_edits'),

    # Weekly Timetable for Specific Entities
    # - Retrieve the weekly timetable for a specific teacher, student, or classroom by its unique identifier
    # - 'pk' represents the UUID of the teacher, student, or classroom
    path('teacher-view-week/<str:pk>/', time_table_views.fetch_all_teachers_weekly_timetable, name='teacher_week_timetable'),
    path('student-view-week/<str:pk>/', time_table_views.fetch_all_students_weekly_timetable, name='student_week_timetable'),
    
    
    path('teacher-timetable-week/<str:pk>/', time_table_views.get_teacher_week_timetable, name='week_timetable_teacher'),
    path('classroom-timetable-week/<str:pk>/', time_table_views.get_classroom_week_timetable, name='classroom_week_timetable'),

    # Download Timetables (for teachers and classrooms)
    # - Download the weekly timetable for a specific teacher or classroom in a file format
    # - 'pk' represents the unique identifier for the teacher or classroom timetable
    path('download-teacher-timetable/<uuid:pk>/', download_timetable_files_views.download_teacher_timetable, name='download_teacher_timetable'),
    path('download-classroom-timetable/<uuid:pk>/', download_timetable_files_views.download_classroom_timetable, name='download_classroom_timetable'),
    
    
    # path('download-teacher-timetable/<uuid:pk>/', download_timetable_files_views.download_teacher_timetable, name='download_teacher_timetable'),
    path('download-whole-classroom-timetable/<uuid:pk>/', download_timetable_files_views.abbreviated_student_timetable_file_export, name='download_classroom_timetable'),
    path('download-whole-classroom-timetable/', download_timetable_files_views.abbreviated_student_timetable_file_export, name='download_classroom_timetable'),
    path('download-whole-teacher-timetable/<uuid:pk>/', download_timetable_files_views.abbreviated_teacher_timetable_file_export, name='download_classroom_timetable'),
    path('download-whole-teacher-timetable/', download_timetable_files_views.abbreviated_teacher_timetable_file_export, name='download_classroom_timetable'),
    
    
    path('send-email/', time_table_views.send_email, name='send_email_to_teacher'),
    
    
    path('create-day-timetable/', day_timetable_views.create_day_timetable, name='create-day-timetable'),
    path('day-timetable-date/delete/<uuid:pk>/', day_timetable_views.delete_day_timetable_date, name='delete_day_timetable_date'),
    path('submit-custom-teacher-day-timetable/<uuid:pk>/<str:date_str>/', day_timetable_views.submit_teacher_custom_day_timetable_edits, name='submit_teacher_timetable_edits'),
    path('submit-custom-student-day-timetable/<uuid:pk>/<str:date_str>/', day_timetable_views.submit_student_custom_day_timetable_edits, name='submit_student_timetable_edits'),

    path('teacher-replacement/', day_timetable_views.process_teacher_replacement, name='teacher_replacement'),
]
