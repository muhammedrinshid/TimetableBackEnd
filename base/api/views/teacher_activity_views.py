from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers, status
from rest_framework.response import Response
from django.db.models import Q, Count
from datetime import datetime
from ..serializer.teacher_activity_serializer import TeacherActivitySummarySerializer
from rest_framework.permissions import IsAuthenticated
from ...models import Teacher
from ...time_table_models import TeacherActivityLog




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retrieve_teacher_activity_summary(request):
    """
    Retrieve summary of teacher activities (leaves and extra loads) within a specified date range.
    
    Query Parameters:
    - start_date: Start date of the activity log (format: YYYY-MM-DD)
    - end_date: End date of the activity log (format: YYYY-MM-DD)
    
    Returns:
    - A summary of leaves and extra loads for each teacher
    """
    # Validate and parse date parameters
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    
    # Check if both dates are provided
    if not start_date_str or not end_date_str:
        return Response(
            {"error": "Both start_date and end_date are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate date range
    if start_date > end_date:
        return Response(
            {"error": "Start date must be before or equal to end date"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Aggregate activities for each teacher
    teacher_activities = []
    
    # Fetch all teachers to ensure we include teachers with zero activities
    teachers = Teacher.objects.filter(school=request.user)
    
    for teacher in teachers:
        # Count leaves for the primary teacher
        leaves_count = TeacherActivityLog.objects.filter(
            primary_teacher=teacher,
            activity_type='leave',
            date__range=[start_date, end_date]
        ).count()
        leave_days_count = TeacherActivityLog.objects.filter(
        primary_teacher=teacher,
        activity_type='leave',
        date__range=[start_date, end_date]
        ).values('date').distinct().count()
        
        # Count extra loads for the primary teacher
        extra_loads_count = TeacherActivityLog.objects.filter(
            primary_teacher=teacher,
            activity_type='extra_load',
            date__range=[start_date, end_date]
        ).count()
        extra_load_days_count = TeacherActivityLog.objects.filter(
        primary_teacher=teacher,
        activity_type='extra_load',
        date__range=[start_date, end_date]
         ).values('date').distinct().count()
      
        teacher_activities.append({
            'teacher': teacher,
            'leaves_count': leaves_count,
            'extra_loads_count': extra_loads_count,
            'leave_days_count': leave_days_count,
            'extra_load_days_count': extra_load_days_count
        })
        
    
    # Serialize the results
    serializer = TeacherActivitySummarySerializer(teacher_activities, many=True)
    
    return Response({
        'total_teachers_with_activities': len(teacher_activities),
        'teacher_activity_summary': serializer.data
    }, status=status.HTTP_200_OK)