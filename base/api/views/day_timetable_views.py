from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from django.utils.dateparse import parse_date
from django.utils import timezone
from ...time_table_models import Timetable, StandardLevel, ClassSection, \
    Course, Tutor, ClassroomAssignment, Timeslot, Lesson, DayClassSection, \
    LessonClassSection, TimeTableDaySchedule, DayTimetable, DayTimetableDate, DayLesson,DayTutor \
    ,DayCourse,DayClassroomAssignment,DayLessonClassSection,DayStandardLevel,Room,TeacherActivityLog,DayTimeTablePeriod
from ..serializer.time_table_serializer import TeacherDayTimetableSerializer, \
    StudentDayTimetableSerializer,TimeTableDayScheduleSerializer,TeacherDayTimetableSerializerForSpecificDay,StudentDayTimetableSerializerForSpecificDay,TeacherSessionSerializerForSpecificDay
from django.db.models import Prefetch
from ...models import Teacher,Subject
from .time_table_views import get_teacher_day_timetable as get_teacher_day_timetable_from_default,get_student_day_timetable as get_student_day_timetable_from_default
from rest_framework.exceptions import NotFound, PermissionDenied

from collections import defaultdict
from rest_framework import status

from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from rest_framework.exceptions import ValidationError
import traceback


import uuid


def get_student_specific_day_timetable(day_timetable):
    # Validate input
    if not day_timetable:
        raise ValueError("The day_timetable parameter is required.")
    
    # Fetch class sections with related data
    class_sections = DayClassSection.objects.filter(
        day_timetable=day_timetable
    ).select_related(
        'classroom__standard', 'classroom__room'
    ).prefetch_related(
        Prefetch(
            'day_lessons',
            queryset=DayLesson.objects.filter(
                day_timetable=day_timetable,
            ).select_related(
                'course', 'allotted_teacher__teacher', 'classroom_assignment__room',
            ).prefetch_related(
                'class_section_assignments'
            ),
            to_attr='day_class_lessons'
        )
    ).order_by(
        'classroom__standard__short_name',
        'division'
    )

    if not class_sections.exists():
        raise ValueError("No class sections found for the given day timetable.")

    day_timetable_data = []

    # Process each class section
    for class_section in class_sections:
        # Group lessons by period
        period_lessons = defaultdict(list)
        for lesson in class_section.day_class_lessons:
            period_lessons[lesson.period - 1].append(lesson)
        
        # Process each period's lessons into groups
        formatted_sessions = []
        for period in range(day_timetable.teaching_slots):
            lessons = period_lessons.get(period, [])
            if not lessons:
                formatted_sessions.append([])  # Empty period
                continue

            # Group lessons by type and elective group
            lesson_groups = []
            processed_lessons = set()

            # Group elective lessons with the same elective_group_id
            elective_groups = defaultdict(list)
            for lesson in lessons:
                if lesson.is_elective and lesson.elective_group_id and lesson not in processed_lessons:
                    elective_groups[lesson.elective_group_id].append(lesson)
                    processed_lessons.add(lesson)

            # Add each elective group as a separate bundle
            for group_lessons in elective_groups.values():
                lesson_groups.append(group_lessons)

            # Handle remaining lessons (single electives and core subjects)
            for lesson in lessons:
                if lesson not in processed_lessons:
                    lesson_groups.append([lesson])

            formatted_sessions.append(lesson_groups)

        # Add data for the current class section
        day_timetable_data.append({
            'classroom': class_section,
            'sessions': formatted_sessions
        })

    return day_timetable_data

# Fetching results with better error handling


def get_teacher_specific_day_timetable(user, day_timetable):
    # Validate inputs
    if not user or not day_timetable:
        raise ValidationError("User and day_timetable are required parameters.")
    
    tutors = DayTutor.objects.filter(school=user, day_timetable=day_timetable)
    if not tutors.exists():
        raise Http404("No tutors found for the specified day timetable.")
    
    day_timetable_data = []

    for tutor in tutors:
        sessions = [[] for _ in range(day_timetable.teaching_slots)]

        lessons = DayLesson.objects.filter(
            day_timetable=day_timetable,
            allotted_teacher=tutor,
        ).order_by('period')
        
        for lesson in lessons:
            sessions[lesson.period - 1].append(lesson)
        
        # Ensure all slots have at least [None] if empty
        sessions = [[None] if not s else s for s in sessions]
        
        if any(sessions):  # Add to timetable only if there are any sessions
            day_timetable_data.append({
                'instructor': tutor,
                'sessions': sessions,
            })

    if not day_timetable_data:
        raise Http404("No sessions found for any tutors.")
    
    return day_timetable_data






@api_view(['GET'])
def get_whole_teacher_single_day_timetable(request, date_str):
    """
    Retrieve teacher's timetable for a specific date
    
    Workflow:
    1. Parse the date string
    2. Check if a TimetableDate exists for this school and date
    3. If exists, use the specific day timetable
    4. If not, fall back to default timetable
    """
    user = request.user

    # Parse the date
    try:
        specific_date = parse_date(date_str)
        if not specific_date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=400
            )
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=400
        )

    # Determine day of week
    day_of_week = specific_date.strftime('%a').upper()

    # First, check if a specific TimetableDate exists for this date and school
    timetable_date = DayTimetableDate.objects.filter(
        school=user, 
        date=specific_date
    ).first()

    # If a specific timetable exists for this date
    if timetable_date and timetable_date.day_timetable:
        # Use the specific day timetable
        try:

             day_timetable_for_specific_date = get_teacher_specific_day_timetable(user, timetable_date.day_timetable)
             
        except Exception as e:
                error_details = traceback.format_exc()  # Captures the full traceback
                print("error_details", error_details)
                return Response(
                    {"error": "An error occurred while fetching the teacher's day timetable.", "details": str(e)},
                    status=500
                )

        # Add present status for instructors
        serializer = TeacherDayTimetableSerializerForSpecificDay(
            day_timetable_for_specific_date, 
            many=True,
            context={
                    'specific_date': specific_date,
                    'academic_year_start': user.academic_schedule.academic_year_start,
                    'academic_year_end': user.academic_schedule.academic_year_end,
                }
        )

       

        for data in serializer.data:
            if "instructor" in data:
                # Initialize all periods as present (True)
                present = [True] * timetable_date.day_timetable.teaching_slots
                
                # Fetch leave logs for the primary teacher (instructor) on the specific date
                leave_logs = TeacherActivityLog.objects.filter(
                    primary_teacher_id=data["instructor"]["id"],
                    date=specific_date,
                    activity_type="leave"
                ).values_list("period", flat=True)
                
                # Mark the periods in leave_logs as False
                for period in leave_logs:
                    present[period - 1] = False  # Subtract 1 to match zero-based index
                
            data["instructor"]["present"] = present
            
        response_data = {
            "day_timetable": serializer.data,
            "day_schedules":  {"day":day_of_week,"teaching_slots":timetable_date.day_timetable.teaching_slots},
            "date": date_str,
            "is_custom_timetable": True,
            "custom_timetable_id":{
                "timetable_date_id":timetable_date.id,
                "day_timetable_id":timetable_date.day_timetable.id
                
                },
            "active_timetable_id":timetable_date.day_timetable.timetable.id

        }
        return Response(response_data)

    # If no specific timetable, fall back to default
    # Check if the default timetable exists
    timetable = Timetable.objects.filter(school=user, is_default=True).first()
    if not timetable:
        return Response(
            {"error": "No default timetable found for the user's school."},
            status=404
        )

    try:
        # Get the day schedule for the specific day of week
        day_schedule = timetable.day_schedules.get(day=day_of_week)
    except TimeTableDaySchedule.DoesNotExist:
        response_data = {
            "day_timetable": [],
            "day_schedules": {
                "day": day_of_week,
                "teaching_slots": 0,
            },
            "date": date_str,
            "is_custom_timetable": False,
            "custom_timetable_id":None,
            "active_timetable_id":timetable.id,

        }
        return Response(response_data)

    # Get the teacher's day timetable from default
    try:
        day_timetable = get_teacher_day_timetable_from_default(user, timetable, day_schedule)
    except Exception as e:
      
        return Response(
            {"error": "An error occurred while fetching the teacher's day timetable.", "details": str(e)},
            status=500
        )
    # Serialize the data
    serializer = TeacherDayTimetableSerializer(day_timetable, many=True)
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedule)

    # Add present status for instructors
    for data in serializer.data:
        if "instructor" in data:
            data["instructor"]["present"] = [True] * day_schedule.teaching_slots
    
    response_data = {
        "day_timetable": serializer.data,
        "day_schedules": day_schedule_serializer.data,
        "date": date_str,
        "is_custom_timetable": False,
        "custom_timetable_id":None,
        "active_timetable_id":timetable.id,


    }

    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whole_student_single_day_timetable(request, date_str):
    """
    Retrieve student's timetable for a specific date
    
    Similar workflow to teacher timetable view
    """
    user = request.user
    
    # Parse the date
    try:
        specific_date = parse_date(date_str)
        if not specific_date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=400
            )
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=400
        )

    # Determine day of week
    day_of_week = specific_date.strftime('%a').upper()

    # First, check if a specific TimetableDate exists for this date and school
    timetable_date = DayTimetableDate.objects.filter(
        school=user, 
        date=specific_date
    ).first()

    # If a specific timetable exists for this date
    if timetable_date and timetable_date.day_timetable:
        
        
        try:

             day_timetable_for_specific_date = get_student_specific_day_timetable( timetable_date.day_timetable)
             
        except Exception as e:
                return Response(
                    {"error": "An error occurred while fetching the teacher's day timetable.", "details": str(e)},
                    status=500
                )


        
        serializer = StudentDayTimetableSerializerForSpecificDay(
            day_timetable_for_specific_date, 
            many=True
        )
 
   
        response_data = {
            "day_timetable": serializer.data,
            "day_schedules": {"day":day_of_week,"teaching_slots":timetable_date.day_timetable.teaching_slots},
            "date": date_str,
            "is_custom_timetable": True,
            "custom_timetable_id":{
                "timetable_date_id":timetable_date.id,
                "day_timetable_id":timetable_date.day_timetable.id
                
                },
            "active_timetable_id":timetable_date.day_timetable.timetable.id


        }
        return Response(response_data)

    # If no specific timetable, fall back to default
    # Check if the default timetable exists
    timetable = Timetable.objects.filter(school=user, is_default=True).first()
    if not timetable:
        return Response(
            {"error": "No default timetable found for the user's school."},
            status=404
        )

    try:
        # Get the day schedule for the specific day of week
        day_schedule = timetable.day_schedules.get(day=day_of_week)
    except TimeTableDaySchedule.DoesNotExist:
        response_data = {
            "day_timetable": [],
            "day_schedules": {
                "day": day_of_week,
                "teaching_slots": 0,
            },
            "date": date_str,
            "is_custom_timetable": False,
            "custom_timetable_id":None,
            "active_timetable_id":None


        }
        return Response(response_data)

    # Get the student's day timetable from default
    try:
        day_timetable = get_student_day_timetable_from_default(user, timetable, day_schedule)
    except Exception as e:
        return Response(
            {"error": "An error occurred while fetching the student's day timetable.", "details": str(e)},
            status=500
        )

    # Serialize the data
    serializer = StudentDayTimetableSerializer(day_timetable, many=True)
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedule)

    response_data = {
        "day_timetable": serializer.data,
        "day_schedules": day_schedule_serializer.data,
        "date": date_str,
        "is_custom_timetable": False,
        "custom_timetable_id":None,
        "active_timetable_id":timetable.id,


    }

    return Response(response_data)







@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_day_timetable(request):
    try:
        # Extract data from request

        date = request.query_params.get('date')
                # Extract day_of_week and validate it
        day_of_week = request.query_params.get('day_of_week')
        active_timetable_id = request.query_params.get('active_timetable_id')

        # Check if the day_of_week is valid
        if not day_of_week:
            return Response({"error": "Day of week is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not active_timetable_id:
            return Response({"error": "Active timetable ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract 'week_timetable' and check its validity
        week_timetable = request.data.get("week_timetable")
        if not week_timetable:
            return Response({"error": "Week timetable is missing"}, status=status.HTTP_400_BAD_REQUEST)

        # Try to get the data for the specified day of the week
        updated_data = week_timetable.get(day_of_week)
        if updated_data is None:
            return Response({"error": f"No data found for day: {day_of_week}"}, status=status.HTTP_400_BAD_REQUEST)


        # Validate inputs
        if not date or not day_of_week:
            return Response({
                "error": "Date and day of week are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine max teaching slots
        max_teaching_slots = max(
            len(teacher_data.get('sessions', [])) 
            for teacher_data in updated_data
        )
        try:
             # Attempt to retrieve the Timetable object using the ID
            active_timetable = Timetable.objects.get(id=active_timetable_id,school=request.user)
        except Timetable.DoesNotExist:
            # If the timetable does not exist, return an error
            return Response({"error": "Timetable with the given ID does not exist"}, status=status.HTTP_404_NOT_FOUND)
        # Create DayTimetable
        day_timetable = DayTimetable.objects.create(
            timetable=active_timetable,  # Assuming this exists
            school=request.user,
            teaching_slots=max_teaching_slots,
            auto_generated=False
        )
        # Fetch the source day schedule using TimetableSchedule
        source_day_schedule = TimeTableDaySchedule.objects.filter(
            table=active_timetable,
            day=day_of_week  # Replace `some_day` with the appropriate logic
        ).first()

        if source_day_schedule:
            day_timetable = DayTimetable.objects.create(
                timetable=active_timetable,
                school=request.user,
                teaching_slots=source_day_schedule.teaching_slots,
                auto_generated=False
            )
            
            # Iterate through periods and create DayTimeTablePeriod entries
            for period in source_day_schedule.periods.all():
                DayTimeTablePeriod.objects.create(
                    day_timetable=day_timetable,
                    period_number=period.period_number,
                    start_time=period.start_time,
                    end_time=period.end_time
                )


        # Create DayTimetableDate
        day_timetable_date = DayTimetableDate.objects.create(
            school=request.user,
            date=date,
            day_of_week=day_of_week,
            day_timetable=day_timetable
        )

        # Process each teacher's data
        for teacher_data in updated_data:
            instructor = teacher_data.get('instructor', {})
            # Find or create DayTutor
            day_tutor, _ = DayTutor.objects.get_or_create(
                teacher_id=instructor.get('id'),
                name=instructor.get('name'),
                day_timetable=day_timetable,
                school=request.user
            )

            # Process each session for the teacher
            for period, sessions in enumerate(teacher_data.get('sessions', []), 1):
               
                for session in sessions:
                     # Skip the session if any critical field is missing or null
                    if not session.get('subject') or not session.get('subject_id') or not session.get('room') or not session.get('class_details'):
                        continue  # Skip this session if it has missing data
                    # Find or create DayCourse
                    day_course, _ = DayCourse.objects.get_or_create(
                        subject_id=session.get('subject_id'),
                        name=session.get('subject'),
                        day_timetable=day_timetable,
                        school=request.user
                    )

                    # Create DayClassroomAssignment
                    room = session.get('room', {})
                    day_classroom_assignment, _ = DayClassroomAssignment.objects.get_or_create(
                        room_id=room.get('id'),
                        name=room.get('name'),
                        capacity=room.get('capacity', 0),
                        room_type=room.get('room_type', 'CLASSROOM'),
                        timetable=day_timetable,
                        school=request.user
                    )

                    # Find or create DayStandardLevel and DayClassSection
                    day_lesson = DayLesson.objects.create(
                            day_timetable=day_timetable,
                            school=request.user,
                            course=day_course,
                            allotted_teacher=day_tutor,
                            classroom_assignment=day_classroom_assignment,
                            is_elective=session.get('type') == 'Elective',
                            elective_subject_name=session.get('elective_subject_name'),
                            elective_group_id=session.get('elective_group_id',None),
                            period=period
                        )
                    for class_detail in session.get('class_details', []):
                        # Find or create DayStandardLevel
                        day_standard_level, _ = DayStandardLevel.objects.get_or_create(
                            standard_id=class_detail.get('standard_id'),
                            name=class_detail.get('standard'),
                            day_timetable=day_timetable,
                            school=request.user
                        )

                        # Create DayClassSection
                        day_class_section, _ = DayClassSection.objects.get_or_create(
                            standard=day_standard_level,
                            division=class_detail.get('division'),
                            name=f"{day_standard_level.name} - {class_detail.get('division')}",
                            day_timetable=day_timetable,
                            classroom_id=class_detail.get('id'),
                            school=request.user
                        )
                        DayLessonClassSection.objects.create(
                                day_lesson=day_lesson,
                                class_section=day_class_section,
                                number_of_students=class_detail.get('number_of_students', 0)
                            )

                    
                        
                        # Create DayLessonClassSection
                            

        return Response({
            "message": "Day Timetable created successfully",
            "day_timetable_id": str(day_timetable.id)
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        error_message = str(e)
        error_details = traceback.format_exc()
        # Print the error details to the console or log file
        print("Error occurred:", error_message)
        print("Stack trace:", error_details)
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure the user is authenticated
def delete_day_timetable_date(request, pk):
    try:
        # Retrieve the DayTimetableDate object by its pk (UUID)
        day_timetable_date = DayTimetableDate.objects.get(pk=pk)

        # Check if the day_timetable_date belongs to the user's school
        if day_timetable_date.school != request.user:
            raise PermissionDenied(detail="You do not have permission to delete this record.")
        
    except DayTimetableDate.DoesNotExist:
        raise NotFound(detail="DayTimetableDate not found", code=404)

    # Delete the object
    day_timetable_date.delete()

    # Return a success response
    return Response({"message": "DayTimetableDate deleted successfully"}, status=status.HTTP_204_NO_CONTENT)




@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def submit_teacher_custom_day_timetable_edits(request, pk,date_str):
    user = request.user
   
    try:
        specific_date = parse_date(date_str)
        if not specific_date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=400
            )
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=400
        )
    try:
        
        
        timetable_date = DayTimetableDate.objects.filter(  school=user,date=specific_date ).first()
        timetable = get_object_or_404(DayTimetable, id=pk, school=request.user,timetable_date=timetable_date)
        updated_data = request.data.get("day_timetable")
        print(updated_data)
        if timetable_date and timetable_date.day_timetable:
            with transaction.atomic():
                    for teacher_info in updated_data:
                        instructor = teacher_info['instructor']
                        sessions = teacher_info['sessions']
                        
                        # Get or create tutor
                        tutor = get_or_create_tutor(
                            teacher_id=instructor['id'],
                            teacher_name=f"{instructor['name']} {instructor['surname']}",
                            timetable=timetable,
                            user=user
                        )
                        
                        # Process each session group
                        for period_index, session_group in enumerate(sessions):
                            for session in session_group:
                                lesson_id = session.get('lesson_id')
                                
                                # Skip if no lesson ID
                                if not lesson_id:
                                    continue
                                    
                                lesson = get_object_or_404(
                                    DayLesson,
                                    id=lesson_id,
                                    day_timetable=timetable,
                                    school=user
                                )
                                
                                # Verify teacher qualification
                                subject_id = session.get('subject_id')
                                if subject_id and not tutor.teacher.qualified_subjects.filter(id=subject_id).exists():
                                    return Response(
                                        {"error": f"Teacher {tutor.teacher.name} is not qualified to teach this subject"},
                                        status=status.HTTP_400_BAD_REQUEST
                                    )
                                
                                # 1. Get or create timeslot
                                period = period_index + 1
                                
                                
                                # 2. Get or create classroom assignment if room data exists
                                room_data = session.get('room')
                                if room_data:
                                    classroom_assignment = get_or_create_classroom_assignment(
                                        room_data=room_data,
                                        timetable=timetable,
                                        user=user
                                    )
                                    
                                    # Update classroom assignment if different
                                    if lesson.classroom_assignment != classroom_assignment:
                                        lesson.classroom_assignment = classroom_assignment
                                
                                # Update lesson if needed
                                if (lesson.period != period ):
                                    
                                    lesson.period = period
                                    
                                if ( lesson.allotted_teacher != tutor):
                                    
                                    lesson.allotted_teacher = tutor
                                lesson.save()
                                
            return Response({"message": "Timetable updated successfully"}, status=status.HTTP_200_OK)
            
    except Exception as e:
        error_details = traceback.format_exc()  # Captures the full traceback
        print("error_details", error_details)
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def submit_student_custom_day_timetable_edits(request, pk,date_str):
    user = request.user

    try:
        specific_date = parse_date(date_str)
        if not specific_date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=400
            )
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=400
        )
    try:
        # Get the timetable instance
        timetable_date = DayTimetableDate.objects.filter(  school=user,date=specific_date ).first()
        timetable = get_object_or_404(DayTimetable, id=pk, school=request.user,timetable_date=timetable_date)
        updated_data = request.data.get("day_timetable")
        if timetable_date and timetable_date.day_timetable:
            with transaction.atomic():
                    for classroom_data in updated_data:
                        classroom_id = classroom_data['classroom']['id']
                        
                        # Verify classroom belongs to school
                        classroom_section = get_object_or_404(
                            DayClassSection, 
                            classroom__id=classroom_id,
                            school=request.user,
                            day_timetable=timetable
                        )

                        for period_index, session_group in enumerate(classroom_data['sessions']):
                            # Get or validate timeslot
                          
                            for session in session_group:
                                # Add null check for class_distribution
                                if not session.get('class_distribution'):
                                    continue  # Skip if class_distribution is None or empty
                                
                                for distribution in session['class_distribution']:
                                    # Ensure lesson_id exists in distribution
                                    if not distribution or 'lesson_id' not in distribution:
                                        continue  # Skip if distribution is None or lesson_id is missing
                                    
                                    # Validate teacher data exists
                                    if not distribution.get('teacher') or 'id' not in distribution['teacher']:
                                        continue  # Skip if teacher data is missing

                                    # Validate room data exists
                                    if not distribution.get('room'):
                                        continue  # Skip if room data is missing

                                    lesson = get_object_or_404(
                                        DayLesson, 
                                        id=distribution['lesson_id'],
                                        day_timetable=timetable,
                                        school=request.user
                                    )

                                    # Verify lesson belongs to correct classroom
                                    if not lesson.class_sections.filter(
                                        classroom__id=classroom_id
                                    ).exists():
                                        return Response(
                                            {"error": "Lesson does not belong to this classroom"},
                                            status=status.HTTP_400_BAD_REQUEST
                                        )

                                    # Update timeslot if different
                                    if lesson.period != period_index+1:
                                        lesson.period = period_index+1

                                    # Handle teacher update
                                    teacher_id = distribution['teacher']['id']
                                    tutor = get_or_create_tutor(
                                        teacher_id, 
                                        distribution['teacher']['name'],
                                        timetable, 
                                        request.user
                                    )
                                    
                                    if lesson.allotted_teacher != tutor:
                                        lesson.allotted_teacher = tutor

                                    # Handle room update
                                    room_data = distribution['room']
                                    classroom_assignment = get_or_create_classroom_assignment(
                                        room_data,
                                        timetable,
                                        request.user
                                    )
                                    
                                    if lesson.classroom_assignment != classroom_assignment:
                                        lesson.classroom_assignment = classroom_assignment

                                    lesson.save()

            return Response({"message": "Timetable updated successfully"})
        else:
            pass
    except Exception as e:
        error_details = traceback.format_exc()  # Captures the full traceback
        print("error_details", error_details)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )






def get_or_create_tutor(teacher_id, teacher_name, timetable, user):
    teacher = get_object_or_404(Teacher, id=teacher_id, school=user)
    tutor, created = DayTutor.objects.get_or_create(
        teacher=teacher,
        day_timetable=timetable,
        school=user,
        defaults={'name': teacher_name}
    )
    return tutor

def get_or_create_classroom_assignment(room_data, timetable, user):
    room = get_object_or_404(Room, id=room_data['id'], school=user)
    classroom_assignment, created = DayClassroomAssignment.objects.get_or_create(
        room=room,
        timetable=timetable,
        school=user,
        defaults={
            'name': room_data['name'],
            'room_type': room_data['room_type'],
            'capacity': 0  # Set appropriate default
        }
    )
    return classroom_assignment







@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def process_teacher_replacement(request):
    """
    Process teacher replacement with activity logging
    """
    # Extract data from request
    day_timetable_id = request.data.get('day_timetable_id')
    original_teacher_id = request.data.get('original_teacher_id')
    replacement_teacher_id = request.data.get('replacement_teacher_id')
    day_lesson_id = request.data.get('day_lesson_id')
    subject_id = request.data.get('subject_id')
    is_extra_workload_logged = request.data.get('isExtraWorkloadLogged', False)
    is_leave_marked = request.data.get('isLeaveMarked', False)
    replacement_date = request.data.get('date')
    replacement_period = request.data.get('period')
    # Validate input
    if not all([day_timetable_id, original_teacher_id, replacement_teacher_id, 
                day_lesson_id, subject_id, replacement_date, replacement_period]):
        return Response({
            'error': 'Missing required parameters'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Retrieve objects with school context
        day_timetable = get_object_or_404(
            DayTimetable, 
            id=day_timetable_id, 
            school=request.user
        )
        original_teacher = get_object_or_404(
            Teacher, 
            id=original_teacher_id
        )
        replacement_teacher = get_object_or_404(
            Teacher, 
            id=replacement_teacher_id
        )
        day_lesson = get_object_or_404(
            DayLesson, 
            id=day_lesson_id, 
            day_timetable=day_timetable
        )
        subject = get_object_or_404(
            Subject, 
            id=subject_id
        )

        # Handle Extra Load Logging
            # Check for conflicting leave activity
        conflicting_leave = TeacherActivityLog.objects.filter(
            primary_teacher=replacement_teacher,
            date=replacement_date,
            period=replacement_period,
            activity_type='leave'
        ).first()

        if conflicting_leave:
            # Remove conflicting leave activity
            conflicting_leave.delete()

        else:
            if is_extra_workload_logged:
                TeacherActivityLog.objects.create(
                    date=replacement_date,
                    period=replacement_period,
                    activity_type='extra_load',
                    primary_teacher=replacement_teacher,
                    substitute_teacher=original_teacher,
                    day_lesson=day_lesson
                )

        # Handle Leave Marking
            # Check for existing extra load activity
        existing_extra_load = TeacherActivityLog.objects.filter(
            primary_teacher=original_teacher,
            date=replacement_date,
            period=replacement_period,
            activity_type='extra_load'
        ).first()

        if existing_extra_load:
            # Remove existing extra load activity
            existing_extra_load.delete()
            
        else:
            
            if is_leave_marked:

                 # Create leave activity log
                TeacherActivityLog.objects.create(
                    date=replacement_date,
                    period=replacement_period,
                    activity_type='leave',
                    primary_teacher=original_teacher,
                    day_lesson=day_lesson
                )

        # Validate current lesson's teacher
        if day_lesson.allotted_teacher.teacher != original_teacher:
            return Response({
                'error': 'Current lesson\'s teacher does not match the original teacher'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get or create Day Tutor for replacement teacher
        day_tutor, _ = DayTutor.objects.get_or_create(
            teacher=replacement_teacher,
            school=request.user,
            day_timetable=day_timetable
        )

        # Update lesson details
        day_lesson.allotted_teacher = day_tutor
        
        # Update or create Day Course
        day_course, _ = DayCourse.objects.get_or_create(
            day_timetable=day_timetable,
            school=request.user,
            subject=subject,
            name=subject.name
        )
        day_lesson.course = day_course
        day_lesson.save()
        day_lesson_serializer = TeacherSessionSerializerForSpecificDay(day_lesson)
        return Response({
            'message': 'Teacher replacement processed successfully',
            'day_lesson': day_lesson_serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = str(e)
        error_details = traceback.format_exc()
        # Print the error details to the console or log file
        print("Error occurred:", error_message)
        print("Stack trace:", error_details)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)