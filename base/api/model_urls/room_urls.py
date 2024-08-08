from django.urls import path
from ..views import room_views
urlpatterns = [
    
                path('rooms/', room_views.room_manager, name='room-list-create'),
                path('rooms/<uuid:pk>/', room_views.room_manager, name='room-detail'),
                path('rooms/', room_views.school_rooms, name='school-rooms'),
                path('non-occupied-rooms/', room_views.get_non_occupied_rooms, name='non-occupied-rooms'),
                path('check-availability/<int:room_number>/', room_views.check_room_number_availability, name='check-room-number'),
                path('exclude_classrooms/', room_views.school_rooms_except_classrooms, name='school_rooms_except_classrooms'),



]