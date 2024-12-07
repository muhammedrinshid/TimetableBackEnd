
# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, F,Q
from ...models import  Teacher
from ...time_table_models import Timetable,Lesson
from ..serializer.analytics_serializer import TeacherUtilizationSerializer
from datetime import timedelta

from django.utils.timezone import now

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
    total_slots = user.academic_schedule.total_weekly_teaching_slots
    
    # Get teachers with their working sessions count
    last_week_start = now().date() - timedelta(days=7)
    last_week_end = now().date()

    # Fetch teachers with annotations for working sessions, leaves, and extra loads
    teachers = Teacher.objects.filter(school=user).annotate(
        working_sessions_in_a_week=Count(
            'tutors__allotted_lessons',
            filter=Q(
                tutors__allotted_lessons__timetable=timetable,
                tutors__timetable=timetable
            ),
            distinct=True
        ),
        leaves_last_week=Count(
            'activities',
            filter=Q(
                activities__activity_type='leave',
                activities__date__range=(last_week_start, last_week_end)
            ),
            distinct=True
        ),
        extra_loads_last_week=Count(
            'activities',
            filter=Q(
                activities__activity_type='extra_load',
                activities__date__range=(last_week_start, last_week_end)
            ),
            distinct=True
        )
    )

    # Calculate free sessions and include workload data
    for teacher in teachers:
        teacher.free_sessions_in_a_week = total_slots - teacher.working_sessions_in_a_week-teacher.leaves_last_week - teacher.extra_loads_last_week
        
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

