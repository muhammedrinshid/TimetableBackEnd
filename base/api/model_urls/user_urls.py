from django.urls import path
from ..views import user_views

urlpatterns = [
    path('info/', user_views.user_info, name='get-user-info'),
    path('update-profile-image/', user_views.update_profile_image, name='update_profile_image'),

    path('level/<str:pk>/',user_views.level_create_update,name='update-existing-level'),
    path('levels/',user_views.levels,name='get-all-levels'),
    path('subjects/',user_views.subjects,name='get-all-subjects'),
    path('user-constraints/', user_views.user_constraint_settings, name='user_constraint_settings'),


    path('level/',user_views.level_create_update,name='create-new-level'),
]