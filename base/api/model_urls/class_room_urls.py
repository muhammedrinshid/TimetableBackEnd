from django.urls import path
from ..views import class_room_views
urlpatterns = [
    
            path('create-standard/',class_room_views.create_standard_and_classrooms , name='create-standard-with-classrooms'),
            path('elective-subject-add/<str:pk>/', class_room_views.elective_subject_add_view, name='elective-subject-add'),

            path('classroom/<str:pk>/',class_room_views.classroom_instance_manager , name='classrooms-updation-deletion'),
            
            path('classroom/',class_room_views.classroom_instance_manager , name='classrooms-detail-view'),
            path('standard/<str:pk>/',class_room_views.standard_instance_manager , name='classrooms-updation-deletion'),
            path('grades-standards-classrooms/', class_room_views.get_user_grades_standards_classrooms, name='grades-standards-classrooms'),
            path('add-division/', class_room_views.add_new_division, name='add_new_division'),
            path('subjects-with-teachers/<str:pk>/', class_room_views.list_subjects_with_available_teachers, name='subjects-with-teachers'),
            path('assign-subjects-to-all-classrooms/<str:pk>/', class_room_views.assign_subjects_to_all_classrooms, name='assign-subjects-to-all-classrooms'),
            path('update-elective-group/', class_room_views.update_elective_group, name='update-elective-group'),




]