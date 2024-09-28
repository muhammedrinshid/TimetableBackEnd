from django.urls import path
from ..views import class_room_views
urlpatterns = [
    
            path('create-grade/',class_room_views.create_grade_and_classrooms , name='create-grade-with-classrooms'),
            path('elective-subject-add/<str:pk>/', class_room_views.elective_subject_add_view, name='elective-subject-add'),
            path('class-subject-detail/<uuid:pk>/', class_room_views.update_class_subject, name='update_class_subject'),

            path('classroom/<str:pk>/',class_room_views.classroom_instance_manager , name='classrooms-updation-deletion'),
            path('class-subject/<str:pk>/',class_room_views.classsubject_instance_manager , name='class-subject-manager'),
            
            path('classroom/',class_room_views.classroom_instance_manager , name='classrooms-detail-view'),
            path('grade/<str:pk>/',class_room_views.grade_instance_manager , name='classrooms-updation-deletion'),
            path('levels-grades-classrooms/', class_room_views.get_user_levels_grades_classrooms, name='levels-grades-classrooms'),
            path('add-division/', class_room_views.add_new_division, name='add_new_division'),
            path('subjects-with-teachers/<str:pk>/', class_room_views.list_subjects_with_available_teachers, name='subjects-with-teachers'),
            path('assign-subjects-to-all-classrooms/<str:pk>/', class_room_views.assign_subjects_to_all_classrooms, name='assign-subjects-to-all-classrooms'),
            path('assign-subjects-to-single-classroom/<str:pk>/', class_room_views.assign_subjects_to_single_classroom, name='assign-subjects-to-single-classrooms'),
            path('update-elective-group/', class_room_views.update_elective_group, name='update-elective-group'),
            path('level-subjects/', class_room_views.get_level_subjects, name='level_subjects'),




]