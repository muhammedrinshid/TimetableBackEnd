from django.urls import path
from ..views import teacher_views
urlpatterns = [
    
        path('teacher/<str:pk>/',teacher_views.teacher , name='teacher'),
        path('teacher/',teacher_views.teacher , name='create-new-teacher'),
        path('update-profile-image/<str:pk>/', teacher_views.update_teacher_image, name='update_profile_image'),

        path('teachers/',teacher_views.teachers , name='teachers'),
        path('school-subject-teacher-count/', teacher_views.subject_teacher_count, name='school-subject-teacher-count'),

]