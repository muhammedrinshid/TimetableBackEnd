from django.urls import path
from ..views import teacher_views
urlpatterns = [
    
        path('teacher/<str:pk>/',teacher_views.teacher , name='teacher'),
        path('teacher/',teacher_views.teacher , name='create-new-teacher'),
        path('update-profile-image/<str:pk>/', teacher_views.update_teacher_image, name='update_profile_image'),
        path('teachers-without-classroom/', teacher_views.list_teachers_without_classroom, name='list_teachers_without_classroom'),
        path('teachers/',teacher_views.teachers , name='teachers'),
        path('school-subject-teacher-count/', teacher_views.subject_teacher_count, name='school-subject-teacher-count'),
        path('generate-teacher-template/',      teacher_views.generate_teacher_template, name='generate_teacher_template'),
        path('process-teacher-template/',      teacher_views.process_teacher_template, name='process_teacher_template'),
]

