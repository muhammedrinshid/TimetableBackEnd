from django.urls import path
from ..views import user_views

urlpatterns = [
    path('info/', user_views.user_info, name='get-user-info'),
    path('update-profile-image/', user_views.update_profile_image, name='update_profile_image'),

    path('grade/<str:pk>/',user_views.grade_create_update,name='update-existing-grade'),
    path('grades/',user_views.grades,name='get-all-grades'),
    path('subjects/',user_views.subjects,name='get-all-subjects'),
    path('user-constraints/', user_views.user_constraint_settings, name='user_constraint_settings'),


    path('grade/',user_views.grade_create_update,name='create-new-grade'),
]