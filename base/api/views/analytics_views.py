
# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, F,Q
from ...models import  Teacher
from ...time_table_models import Timetable,Lesson
from ..serializer.analytics_serializer import TeacherUtilizationSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_utilization_view(request, pk=None):
    """
    Get teacher utilization statistics for a specific timetable
    """
    user = request.user
    if pk is None:
        timetable = get_object_or_404(Timetable, school=user, is_default=True)
    else:
        timetable = get_object_or_404(Timetable, id=pk,school=user)
    
    # Calculate total slots
    total_slots = len(user.working_days) * (user.teaching_slots)
    
    # Get teachers with their working sessions count
    teachers = Teacher.objects.filter(school=user).annotate(
    working_sessions_in_a_week=Count(
        'tutors__allotted_lessons',
        filter=Q(
            tutors__allotted_lessons__timetable=timetable,
            tutors__timetable=timetable
        ),
        distinct=True  # Add this if there's any chance of duplicate counts
    )
)
    
    # Calculate free sessions for each teacher
    for teacher in teachers:
        teacher.free_sessions_in_a_week = total_slots - teacher.working_sessions_in_a_week
        # if teacher.profile_image:
        #     teacher.profile_image = request.build_absolute_uri(teacher.profile_image.url)
    
    # Calculate header details
    chart_header_details = {
        'total_teachers': teachers.count(),
        'teachers_utilization_capacity': teachers.count() * total_slots,
        'total_classroom_work_sessions': Lesson.objects.filter(
            school=user,
            timetable=timetable
        ).count()
    }
    
    # Prepare data for serializer
    data = {
        'chart_header_details': chart_header_details,
        'chart_details': teachers
    }
    
    serializer = TeacherUtilizationSerializer(data)
    return Response(serializer.data)

