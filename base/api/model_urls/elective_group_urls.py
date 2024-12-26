from django.urls import path
from ..views import elective_group_views
urlpatterns = [
    
        path('groups/', elective_group_views.get_elective_groups, name='elective-group-list'),
        path('standard-elective-subjects/<uuid:pk>/', elective_group_views.get_standard_elective_subjects, name='standard_elective_subjects'),
        path('standard-elective-subjects/', elective_group_views.get_standard_elective_subjects, name='standard_elective_subjects'),
        path('group/<uuid:pk>/', elective_group_views.create_or_update_elective_group, name='create_or_update_elective_group'),
        path('group/', elective_group_views.create_or_update_elective_group, name='create_or_update_elective_group'),
        path('remove-elective-group/<uuid:pk>/', elective_group_views.remove_elective_group_connection, name='remove-elective-group'),


]