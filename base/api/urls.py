from django.urls import path,include
from . import main_views as views


from .main_views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView



urlpatterns = [
    path('', views.getroutes, name='getRoutes'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/',include("base.api.model_urls.user_urls")),
    path('teacher/',include("base.api.model_urls.teacher_urls")),
    path('class-room/',include("base.api.model_urls.class_room_urls")),
    path('room/',include("base.api.model_urls.room_urls")),
    path('time-table/',include("base.api.model_urls.time_table_urls")),
    path('analytics/',include("base.api.model_urls.analytics_urls"))
]