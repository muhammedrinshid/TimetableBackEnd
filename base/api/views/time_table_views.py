from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from ...optapy_solver.solver import run_optimization
from ...time_table_models import Timetable, StandardLevel, ClassSection, Course, Tutor, ClassroomAssignment, Timeslot, Lesson,LessonClassSection,TimeTableDaySchedule,DayChoices,TimeTablePeriod
from django.db import transaction

from django.db.models import Prefetch
from ..serializer.time_table_serializer import TimetableSerializer,TimetableUpdateSerializer
from collections import defaultdict

from rest_framework.decorators import api_view
from rest_framework.response import Response
from ...models import  Teacher, Subject, Room,Classroom,Standard
from ..serializer.time_table_serializer import TeacherDayTimetableSerializer,StudentWeekTimetableSerializer,StudentDayTimetableSerializer,WholeTeacherWeekTimetableSerializer,TimeTableDayScheduleSerializer,TeacherWeekTimetableSerializer,ClassroomWeekTimetableSerializer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from openpyxl import Workbook

from reportlab.lib import colors
import requests


def parse_hard_violations_from_score(score):
    # Implement parsing logic here if score is a string or complex object
    # For example, if score is a string like "-2hard/0soft", parse it accordingly
    # Return the number of hard constraint violations
    hard_violations = 0
    if isinstance(score, str):
        parts = score.split('/')
        for part in parts:
            if 'hard' in part:
                hard_violations = int(part.split('hard')[0])
                break
    return hard_violations


def calculate_performance_score(hard=100, soft=100):
    # If both hard and soft scores are zero, return 100
    if hard == 0 and soft == 0:
        return 100
    
    # Calculate a normalized performance score out of 100
    max_possible_penalty = 100  # You can adjust this based on your scoring scale
    hard_penalty = abs(hard) * 2  # Give more weight to hard score (adjust as needed)
    soft_penalty = abs(soft) / 1000  # Less weight to soft score (adjust as needed)

    # Total penalty should not exceed the max possible penalty
    total_penalty = min(hard_penalty + soft_penalty, max_possible_penalty)
    
    # Calculate the final score out of 100
    performance_score = 100 - total_penalty
    return max(performance_score, 0)  # Ensure score doesn't go below 0

def save_optimization_results(user, solution,score,hard_score,soft_score):
    try:
        with transaction.atomic():
            # Create Timetable
            number_of_lessons = user.teaching_slots

            timetable = Timetable.objects.create(
                name=f"Timetable_{user.username}_{Timetable.objects.filter(school=user).count() + 1}",
                school=user,
                number_of_lessons=number_of_lessons,
                soft_score=soft_score,
                hard_score=hard_score,
                score=score
                
            )
            academic_schedule=user.academic_schedule
            for day_schedule in academic_schedule.day_schedules.all():
                timetable_day_schedule = TimeTableDaySchedule.objects.create(
                    table=timetable,
                    day=day_schedule.day,
                    teaching_slots=day_schedule.teaching_slots
                )
                for period in day_schedule.periods.all():  # Iterate through the periods of the day schedule
                    TimeTablePeriod.objects.create(
                        day_schedule=timetable_day_schedule,
                        period_number=period.period_number,
                        start_time=period.start_time,
                        end_time=period.end_time
        )
             
            for lesson in solution.get_lesson_list():
                # Process Course
                try:
                    subject = lesson.subject
                    if subject is None:
                        raise ValueError("Lesson subject is None")
                    subject_instance = Subject.objects.get(id=subject.id)
                except (Subject.DoesNotExist, AttributeError, ValueError) as e:
                    print(f"Error processing subject: {e}")
                    continue

                course, _ = Course.objects.get_or_create(
                    subject=subject_instance,
                    timetable=timetable,
                    school=user,
                    defaults={'name': subject.name}
                )

                # Process Tutor
                try:
                    teacher = lesson.allotted_teacher
                    if teacher is None:
                        raise ValueError("Allotted teacher is None")
                    teacher_instance = Teacher.objects.get(id=teacher.id)
                except (Teacher.DoesNotExist, AttributeError, ValueError) as e:
                    continue

                tutor, _ = Tutor.objects.get_or_create(
                    teacher=teacher_instance,
                    timetable=timetable,
                    school=user,
                    defaults={'name': teacher.name}
                )

                # Process ClassroomAssignment
                room = lesson.get_allotted_room()
                if room:
                    try:
                        room_instance = Room.objects.get(id=room.id)
                    except (Room.DoesNotExist, AttributeError) as e:
                        print(f"Error processing room: {e}")
                        room_instance = None

                    if room_instance:
                        classroom_assignment, _ = ClassroomAssignment.objects.get_or_create(
                            room=room_instance,
                            timetable=timetable,
                            school=user,
                            defaults={
                                'name': room_instance.name,
                                'capacity': getattr(room_instance, 'capacity', 30),
                                'room_type': getattr(room_instance, 'room_type', 'Standard'),
                                'occupied': getattr(room_instance, 'occupied', False)
                            }
                        )
                    else:
                        classroom_assignment = None
                else:
                    classroom_assignment = None

                # Process Timeslot
                timeslot = lesson.get_timeslot()
                if timeslot:
                    timeslot_obj, _ = Timeslot.objects.get_or_create(
                        day_of_week=timeslot.day_of_week,
                        period=timeslot.period,
                        timetable=timetable,
                        school=user
                    )
                else:
                    timeslot_obj = None

                # Create Lesson
                elective_group_id = lesson.elective.id if lesson.is_elective else None
                lesson_instance = Lesson.objects.create(
                    timetable=timetable,
                    school=user,
                    course=course,
                    allotted_teacher=tutor,
                    classroom_assignment=classroom_assignment,
                    timeslot=timeslot_obj,
                    elective_subject_name=lesson.elective_subject_name,
                    is_elective=lesson.is_elective,
                    elective_group_id=elective_group_id
                )

                # Process ClassSection
                for class_section in lesson.class_sections:
                    try:
                        standard = class_section.standard
                        if standard is None:
                            raise ValueError("Class section standard is None")
                        std_instance = Standard.objects.get(id=standard.id)
                    except (Standard.DoesNotExist, AttributeError, ValueError) as e:
                        print(f"Error processing standard: {e}")
                        continue

                    standard_level, _ = StandardLevel.objects.get_or_create(
                        name=class_section.standard.short_name,
                        timetable=timetable,
                        school=user,
                        standard=std_instance
                    )

                    try:
                        classroom_instance = Classroom.objects.get(id=class_section.id)
                    except (Classroom.DoesNotExist, AttributeError) as e:
                        print(f"Error processing classroom: {e}")
                        continue

                    class_section_obj, _ = ClassSection.objects.get_or_create(
                        classroom=classroom_instance,
                        timetable=timetable,
                        school=user,
                        defaults={
                            'standard': standard_level,
                            'division': class_section.division,
                            'name': class_section.name
                        }
                    )

                    # Get number of students from the lesson's students_distribution
                    students_distribution = lesson.students_distribution or {}
                    number_of_students = students_distribution.get(str(class_section.id), 0)

                    # Create LessonClassSection relationship
                    LessonClassSection.objects.create(
                        lesson=lesson_instance,
                        class_section=class_section_obj,
                        number_of_students=number_of_students
                    )

            return timetable

    except Exception as e:
        # Log the error or handle it as appropriate for your application
        import traceback
        print(f"Error saving optimization results: {str(e)}")
        traceback.print_exc()
        raise


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def run_module_view(request,seconds):
    # Run the optimization process
    optimization_result = run_optimization(seconds,request=request)
    # print(optimization_result)
    # Access the score
    optimaization_score = optimization_result.get_score()  # or use optimization_result.score
    parsed_score = {
        "hard": optimaization_score.getHardScore(),
        "soft": optimaization_score.getSoftScore(),
    }
    calculated_score=calculate_performance_score(parsed_score["soft"],parsed_score["hard"])
    

        
    try:
        # Save the optimization results
        timetable = save_optimization_results(request.user, optimization_result,score=calculated_score,hard_score=parsed_score["hard"],soft_score=parsed_score['soft'],)
        serializer = TimetableSerializer(timetable)
        all_scores={  
            "hard":serializer.data['hard_score'],
            "soft":serializer.data['soft_score'],
            "score":serializer.data['score'],
            
           }
        return Response({
            "message": "Timetable optimization completed and saved",
            "timetable": serializer.data['id'],
             "scores":all_scores,
          
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "message": "Error saving optimization results",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
        
        
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_class_subjects(request):
    user = request.user

    results = {
        "all_class_subjects_have_correct_elective_groups": user.all_class_subjects_have_correct_elective_groups,
        "all_classes_assigned_subjects": user.all_classes_assigned_subjects,
        "all_classes_subject_assigned_atleast_one_teacher": user.all_classes_subject_assigned_atleast_one_teacher,
        "all_classrooms_have_rooms": user.all_classrooms_have_rooms,
        "all_classrooms_have_class_teacher": user.all_classrooms_have_class_teacher,  # Added this line
    }


    reasons = []

    if not user.all_class_subjects_have_correct_elective_groups:
        reasons.append("Not all class subjects have correct elective groups.")
    
    if not user.all_classes_assigned_subjects:
        reasons.append("Not all classes have assigned subjects.")
    
    if not user.all_classes_subject_assigned_atleast_one_teacher:
        reasons.append("Not all class subjects have at least one assigned teacher.")
    if not user.all_classrooms_have_rooms:
        reasons.append("Not all classroom has specific room")
    if not user.all_classrooms_have_class_teacher:
        reasons.append("Not all classrooms have a class teacher.")  # Added this line

    response_data = {
        "results": results,
        "reasons": reasons
    }

    return Response(response_data, status=status.HTTP_200_OK)






@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_timetables(request):
    try:
        # Assuming request.user is linked to a school via the ForeignKey relationship
        school = request.user
        timetables = Timetable.objects.filter(school=school)
        serializer = TimetableSerializer(timetables, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Timetable.DoesNotExist:
        return Response({'error': 'No timetables found for this school.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def set_default_timetable(request, pk):
    try:
        # Retrieve the timetable object
        timetable = Timetable.objects.get(id=pk,school=request.user)
        
        # Set the timetable as default
        timetable.set_as_default()
        
        # Retrieve all timetables for the same school
        timetables = Timetable.objects.filter(school=request.user)
        
        # Serialize all timetables
        serializer = TimetableSerializer(timetables, many=True)
        return Response({'timetables': serializer.data}, status=status.HTTP_200_OK)
    except Timetable.DoesNotExist:
        return Response({'error': 'Timetable not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def timetable_detail(request, timetable_id):
    try:
        timetable = Timetable.objects.get(id=timetable_id)
    except Timetable.DoesNotExist:
        return Response({'error': 'Timetable not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = TimetableUpdateSerializer(timetable, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        timetable.delete()
        return Response({'message': 'Timetable deleted successfully'}, status=status.HTTP_204_NO_CONTENT)










# fetching results
def get_teacher_day_timetable(user, timetable,day_schedule):
    teachers = Teacher.objects.filter(school=user)
    day_timetable = []
    
    for teacher in teachers:
        tutor = Tutor.objects.filter(teacher=teacher, timetable=timetable).first()
        
        if tutor:
            sessions = [[] for _ in range(day_schedule.teaching_slots)]
            
            lessons = Lesson.objects.filter(
                timetable=timetable,
                allotted_teacher=tutor,
                timeslot__day_of_week=day_schedule.day
            ).order_by('timeslot__period')
            
            for lesson in lessons:
                sessions[lesson.timeslot.period - 1].append(lesson)
            sessions=[[None] if not s else s for s in sessions]
            if any(sessions):  # Only add to day_timetable if there are any sessions
                day_timetable.append({
                    'instructor': tutor,
                    'sessions': sessions
                })
    
    return day_timetable

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whole_teacher_single_day_timetable(request, day_of_week):
    user = request.user

    # Check if the timetable exists and is default
    timetable = Timetable.objects.filter(school=user, is_default=True).first()
    if not timetable:
        return Response(
            {"error": "No default timetable found for the user's school."},
            status=404,
        )

    try:
        # Check if the day schedule exists for the provided day_of_week
        day_schedule = timetable.day_schedules.get(day=day_of_week)
    except TimeTableDaySchedule.DoesNotExist:
            response_data = {
                "day_timetable": [],
                "day_schedules": {
                    "day": day_of_week,
                    "teaching_slots": 0,
                },
            }
            return Response(response_data)

    try:
        # Get the teacher's day timetable
        day_timetable = get_teacher_day_timetable(user, timetable, day_schedule)
    except Exception as e:
        return Response(
            {"error": "An error occurred while fetching the teacher's day timetable.", "details": str(e)},
            status=500,
        )

    # Serialize the data
    serializer = TeacherDayTimetableSerializer(day_timetable, many=True)
    serialized_data = serializer.data  # Access serialized data

    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedule)
    for data in serialized_data:
            if "instructor" in data:
                data["instructor"]["present"] = [True] * day_schedule.teaching_slots
    # Prepare response data
    response_data = {
        "day_timetable": serializer.data,
        "day_schedules": day_schedule_serializer.data,
    }

    return Response(response_data)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whole_student_single_day_timetable(request, day_of_week):
    user = request.user

    # Check if the timetable exists and is default
    timetable = Timetable.objects.filter(school=user, is_default=True).first()
    if not timetable:
        return Response(
            {"error": "No default timetable found for the user's school."},
            status=404,
        )

    try:
        # Check if the day schedule exists for the provided day_of_week
        day_schedule = timetable.day_schedules.get(day=day_of_week)
    except TimeTableDaySchedule.DoesNotExist:
        response_data = {
                "day_timetable": [],
                "day_schedules": {
                    "day": day_of_week,
                    "teaching_slots": 0,
                },
            }
        return Response(response_data)

    try:
        # Get the student's day timetable
        day_timetable = get_student_day_timetable(user, timetable, day_schedule)
    except Exception as e:
        return Response(
            {"error": "An error occurred while fetching the student's day timetable.", "details": str(e)},
            status=500,
        )

    # Serialize the data
    serializer = StudentDayTimetableSerializer(day_timetable, many=True)
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedule)

    # Prepare response data
    response_data = {
        "day_timetable": serializer.data,
        "day_schedules": day_schedule_serializer.data,
    }

    return Response(response_data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_all_teachers_weekly_timetable(request,pk=None):
    user = request.user
    if pk is None:
      timetable = Timetable.objects.filter(school=user, is_default=True).first()  # Get the default timetable or None
    else:
        timetable = Timetable.objects.get(school=user, id=pk)
    if not timetable:
        return Response({}, status=200)
    # Get working days
    day_schedules = timetable.day_schedules.all() if timetable else []

    week_timetable = {}
    for day_schedule in day_schedules:
        day_timetable = get_teacher_day_timetable(user, timetable, day_schedule)
        week_timetable[day_schedule.day] = day_timetable
    
    serializer = WholeTeacherWeekTimetableSerializer(week_timetable,working_days=[day_schedule.day for day_schedule in day_schedules])
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedules, many=True)

    response_data = {
            'week_timetable': serializer.data,
            'day_schedules': day_schedule_serializer.data
        }
    return Response(response_data)











def get_student_day_timetable(user, timetable, day_schedule):

    
    class_sections = ClassSection.objects.filter(
        timetable=timetable
    ).select_related(
        'classroom__standard', 'classroom__room'
    ).prefetch_related(
        Prefetch(
            'lessons',
            queryset=Lesson.objects.filter(
                timetable=timetable,
                timeslot__day_of_week=day_schedule.day
            ).select_related(
                'course', 'allotted_teacher__teacher', 'classroom_assignment__room', 'timeslot'
            ).prefetch_related(
                'lessonclasssection_set'
            ),
            to_attr='day_lessons'
        )
    ).order_by(
        'classroom__standard__short_name', 
        'division'
    )

    day_timetable = []

    for class_section in class_sections:
        # First, group lessons by period
        period_lessons = defaultdict(list)
        for lesson in class_section.day_lessons:
            period_lessons[lesson.timeslot.period - 1].append(lesson)
        
        # Now process each period's lessons into groups
        formatted_sessions = []
        for period in range(day_schedule.teaching_slots):
            lessons = period_lessons[period]
            if not lessons:
                formatted_sessions.append([])  # Empty period
                continue
            
            # Group lessons by type and elective group
            lesson_groups = []
            processed_lessons = set()
            
            # First, group elective lessons with same elective_group_id
            elective_groups = defaultdict(list)
            for lesson in lessons:
                if lesson.is_elective and lesson.elective_group_id and lesson not in processed_lessons:
                    elective_groups[lesson.elective_group_id].append(lesson)
                    processed_lessons.add(lesson)
            
            # Add each elective group as a separate bundle
            for group_lessons in elective_groups.values():
                if group_lessons:  # Should always be true
                    lesson_groups.append(group_lessons)
            
            # Handle remaining lessons (single electives without group and core subjects)
            for lesson in lessons:
                if lesson not in processed_lessons:
                    lesson_groups.append([lesson])
            
            formatted_sessions.append(lesson_groups)

        day_timetable.append({
            'classroom': class_section,
            'sessions': formatted_sessions
        })

    return day_timetable





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_all_students_weekly_timetable(request,pk=None):
    user = request.user

    if pk is None:
        timetable = Timetable.objects.filter(school=user, is_default=True).first()  # Get the default timetable or None

        if not timetable:
            return Response({}, status=200)
    else:
        timetable = get_object_or_404(Timetable, id=pk,school=user)
    
    day_schedules = timetable.day_schedules.all() if timetable else []

    week_timetable = {}
    for day_schedule in day_schedules:
        day_timetable = get_student_day_timetable(user, timetable, day_schedule)
        week_timetable[day_schedule.day] = day_timetable
    
    serializer = StudentWeekTimetableSerializer(week_timetable,  working_days=[day_schedule.day for day_schedule in day_schedules])
   
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedules, many=True)

    response_data = {
            'week_timetable': serializer.data,
            'day_schedules': day_schedule_serializer.data
        }
    return Response(response_data)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_whole_student_week_timetable(request, pk):
#     user = request.user
    
#     # Check if pk is provided
#     if pk is None:
#         return Response({"error": "Timetable ID is required"}, status=400)
    
#     # Get the timetable instance
#     try:
#         timetable = Timetable.objects.get(school=user, id=pk)
#     except Timetable.DoesNotExist:
#         return Response({"error": "Timetable not found"}, status=404)
    
#     # Get working days for the user
#     day_schedules = timetable.day_schedules.all() if timetable else []
    
#     # Initialize week timetable
#     week_timetable = {}
    
#     # Iterate over working days
#     for day_schedule in day_schedules:
#         day_timetable = get_student_day_timetable(user, timetable, day_schedule)
#         week_timetable[day_schedules.day] = day_timetable
    
#     # Serialize the week timetable
#     serializer = StudentWeekTimetableSerializer(week_timetable, working_days=[day_schedule.day for day_schedule in day_schedules])
    
#     # Return the response
#     return Response(serializer.data)





# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_whole_teacher_week_timetable(request, pk):
#     user = request.user
    
#     # Check if pk is provided
#     if pk is None:
#         return Response({"error": "Timetable ID is required"}, status=400)
    
#     try:
#         # Get the timetable instance
#         timetable = Timetable.objects.get(school=user, id=pk)
#     except Timetable.DoesNotExist:
#         return Response({"error": "Timetable not found"}, status=404)
#     except Exception as e:
#         return Response({"error": "Internal Server Error"}, status=500)
    
#     # Get working days for the user
#     day_schedules = timetable.day_schedules.all() if timetable else []
    
#     # Initialize week timetable
#     week_timetable = {day_schedules.day: get_teacher_day_timetable(user, timetable, day_schedule) for day_schedule in day_schedules}
    
#     # Serialize the week timetable
#     serializer = WholeTeacherWeekTimetableSerializer(week_timetable,working_days=[day_schedule.day for day_schedule in day_schedules])
#     day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedules, many=True)

#     # Return the response
#     return Response(serializer.data)








@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_classroom_week_timetable(request,pk):
    user = request.user
    timetable = Timetable.objects.filter(school=user, is_default=True).first()  # Get the default timetable or None

    if not timetable:
        return Response({
            'day_timetable': [],
            'day_schedules': []
        }, status=200)

    if pk is not None:
        try:
            classroom=Classroom.objects.get(id=pk,school=user)
            classsection=ClassSection.objects.get(classroom=classroom,timetable=timetable)
            
        except Classroom.DoesNotExist:
            return Response({'error': 'No classroom found for this school.'}, status=status.HTTP_404_NOT_FOUND)
        except  ClassSection.DoesNotExist:
            
            return Response({'error': 'No classroom found for this school.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    day_schedules = timetable.day_schedules.all() if timetable else []

    day_timetable = []
    
    
    
    
    for day_schedule in day_schedules:
        day_lessons = Lesson.objects.filter(
            timetable=timetable,
            timeslot__day_of_week=day_schedule.day,
            class_sections__in=[classsection]
        ).select_related(
            'course', 'allotted_teacher__teacher', 'classroom_assignment__room', 'timeslot'
        
    )
        
        sessions = defaultdict(list)
        for lesson in day_lessons:
            sessions[lesson.timeslot.period - 1].append(lesson)

        formatted_sessions = [sessions[i] for i in range(day_schedule.teaching_slots)]

            
        

        day_timetable.append({
            'day': day_schedule.day,
            'sessions': formatted_sessions
        })
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedules, many=True)

    serializer = ClassroomWeekTimetableSerializer(day_timetable,many=True,context={'class_section': classsection})
    response_data = {
            'day_timetable': serializer.data,
            'day_schedules': day_schedule_serializer.data
        }
    return Response(response_data)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_teacher_week_timetable(request,pk):
    # Get all teachers for the school
    user = request.user
    timetable = Timetable.objects.filter(school=user, is_default=True).first()  # Get the default timetable or None
    day_schedules = timetable.day_schedules.all() if timetable else []

    if not timetable:
        return Response([], status=200)

    if pk is not None:
        try:
            teacher=Teacher.objects.get(id=pk,school=user)
            tutor=Tutor.objects.get(teacher=teacher,timetable=timetable)
            
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found for this school.'}, status=status.HTTP_404_NOT_FOUND)
        except Tutor.DoesNotExist:
             return Response({'error': 'No timetable available for this teacher.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        



    day_timetable = []
    
    
    for day_schedule in day_schedules:
        # Check if there's a Tutor object for this teacher and timetable
        
        # Initialize sessions with None for each period
        sessions = [None] * day_schedule.teaching_slots
        
        # Get all lessons for this tutor on the specified day
        lessons = Lesson.objects.filter(
            timetable=timetable,
            allotted_teacher=tutor,
            timeslot__day_of_week=day_schedule.day
        ).order_by('timeslot__period')
        # Fill in the sessions with actual lesson data
        for lesson in lessons:
            sessions[lesson.timeslot.period - 1] = lesson
        
        # Remove any remaining None values
        # sessions = [s for s in sessions if s is not None]
        if sessions:  # Only add to day_timetable if there are sessions
            day_timetable.append({
                'day': day_schedule.day,
                'sessions': sessions
            })
    
    serializer = TeacherWeekTimetableSerializer(day_timetable,many=True)
    day_schedule_serializer = TimeTableDayScheduleSerializer(day_schedules, many=True)
    response_data = {
            'day_timetable': serializer.data,
            'day_schedules': day_schedule_serializer.data
        }
    return Response(response_data)




@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def submit_teacher_week_timetable_edits(request, pk):
    user = request.user
    timetable = get_object_or_404(Timetable, id=pk, school=user)
    updated_data = request.data.get("week_timetable")
    
    try:
        with transaction.atomic():
            for day, teacher_data in updated_data.items():
                for teacher_info in teacher_data:
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
                                Lesson,
                                id=lesson_id,
                                timetable=timetable,
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
                            timeslot = get_or_create_timeslot(
                                day,
                                period,
                                timetable,
                                user
                            )
                            
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
                            if (lesson.timeslot != timeslot ):
                                
                                lesson.timeslot = timeslot
                                
                            if ( lesson.allotted_teacher != tutor):
                                
                                lesson.allotted_teacher = tutor
                            lesson.save()
                            
        return Response({"message": "Timetable updated successfully"}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
        
        
        
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def submit_student_week_timetable_edits(request, pk):
    try:
        # Get the timetable instance
        timetable = get_object_or_404(Timetable, id=pk, school=request.user)
        updated_data = request.data.get("week_timetable")

        with transaction.atomic():
            for day, classroom_data_list in updated_data.items():
                for classroom_data in classroom_data_list:
                    classroom_id = classroom_data['classroom']['id']
                    
                    # Verify classroom belongs to school
                    classroom_section = get_object_or_404(
                        ClassSection, 
                        classroom__id=classroom_id,
                        school=request.user,
                        timetable=timetable
                    )

                    for period_index, session_group in enumerate(classroom_data['sessions']):
                        # Get or validate timeslot
                        timeslot = get_or_create_timeslot(
                            day, period_index+1, timetable, request.user
                        )
                        
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
                                    Lesson, 
                                    id=distribution['lesson_id'],
                                    timetable=timetable,
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
                                if lesson.timeslot != timeslot:
                                    lesson.timeslot = timeslot

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

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def get_or_create_timeslot(day, period, timetable, user):
    timeslot, created = Timeslot.objects.get_or_create(
        day_of_week=day,
        period=period,
        timetable=timetable,
        school=user,
    )
    return timeslot

def get_or_create_tutor(teacher_id, teacher_name, timetable, user):
    teacher = get_object_or_404(Teacher, id=teacher_id, school=user)
    tutor, created = Tutor.objects.get_or_create(
        teacher=teacher,
        timetable=timetable,
        school=user,
        defaults={'name': teacher_name}
    )
    return tutor

def get_or_create_classroom_assignment(room_data, timetable, user):
    room = get_object_or_404(Room, id=room_data['id'], school=user)
    classroom_assignment, created = ClassroomAssignment.objects.get_or_create(
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
def send_email(request):
    try:
        response = send_simple_message()

        if response.status_code == 200:
            return Response({"message": "Email sent successfully"})
        else:
            return Response({"error": response.text}, status=response.status_code)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

def send_simple_message():
    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Excited User <mailgun@{MAILGUN_DOMAIN}>",
            "to": ["mrappt2001@gmail.com", f"YOU@{MAILGUN_DOMAIN}"],
            "subject": "Hello",
            "text": "Testing some Mailgun awesomeness!"
        }
    )
    
    
    
    
    
    
def abbreviate(word):
    # Split the word by spaces
    parts = word.split()
    
    # Check if the word contains multiple parts
    if len(parts) > 1:
        # If more than one word, take the first letter of each part and capitalize it
        abbreviation = ''.join(part[0].upper() for part in parts)
    else:
        # If it's a single word, take the first three characters and capitalize
        abbreviation = word[:3].capitalize() if len(word) > 3 else word.upper()
    
    return abbreviation

    
    
def get_student_condensed_timetable( timetable):
    """
    Generate a condensed timetable view with simplified class and day representations.
    
    :param user: Current user context
    :param timetable: Timetable object
    :return: List of condensed classroom timetables
    """
    # Fetch day schedules with optimized querying
    day_schedules = timetable.day_schedules.all() if timetable else []
    
    # Prepare base query for class sections with optimized related data fetching
    class_sections = ClassSection.objects.filter(
        timetable=timetable
    ).select_related(
        'classroom__standard', 'classroom__room'
    ).prefetch_related(
        Prefetch(
            'lessons',
            queryset=Lesson.objects.filter(
                timetable=timetable
            ).select_related(
                'course', 'timeslot'
            ).prefetch_related(
                'lessonclasssection_set'
            )
        )
    ).order_by(
        'classroom__standard__short_name', 
        'division'
    )
    
    condensed_timetables = []
    
    for class_section in class_sections:
        # Prepare classroom details
        classroom_details = {
            'standard': class_section.classroom.standard.short_name,
            'division': class_section.division,
            'full_identifier': f"{class_section.classroom.standard.short_name}{class_section.division}"
        }
        
        # Initialize day-wise timetable for this class
        day_timetables = defaultdict(list)
        
        # Process lessons for each day schedule
        for day_schedule in day_schedules:
            # Group lessons by period and day
            period_lessons = defaultdict(lambda: defaultdict(list))
            
            # Filter and group lessons for this specific day
            day_lessons = [
                lesson for lesson in class_section.lessons.all() 
                if lesson.timeslot.day_of_week == day_schedule.day
            ]
            
            for lesson in day_lessons:
                period = lesson.timeslot.period - 1
                period_lessons[period][lesson.course.name].append({
                    'subject': abbreviate(lesson.course.name),
                    'is_elective': lesson.is_elective
                })
            
            # Create structured day timetable
            day_periods = []
            for period in range(day_schedule.teaching_slots):
                period_subjects = list(period_lessons[period].values())
                # Flatten nested lists of subjects for the period
                day_periods.append([
                    subject_info 
                    for subjects in period_subjects 
                    for subject_info in subjects
                ])
            
            day_timetables[day_schedule.day] = day_periods
        
        # Combine classroom details with day timetables
        condensed_timetable = {
            'class_details': classroom_details,
            'timetable_rows': dict(day_timetables)
        }
        
        condensed_timetables.append(condensed_timetable)
    
    return condensed_timetables

def get_teacher_condensed_timetable(timetable):
    teachers = Teacher.objects.filter(school=timetable.school)
    condensed_timetable = []
    
    for teacher in teachers:
        tutor = Tutor.objects.filter(teacher=teacher, timetable=timetable).first()
        
        if tutor:
            teacher_entry = {
                "teacher_details": {
                "full_name": f"{tutor.teacher.name} {tutor.teacher.surname}",
                    "teacher_id": tutor.teacher.teacher_id
                },
                "timetable_rows": {}
            }
            
            # Get all day schedules for this timetable
            day_schedules = timetable.day_schedules.all()
            
            for day_schedule in day_schedules:
                # Find lessons for this teacher on this specific day
                lessons = Lesson.objects.filter(
                    timetable=timetable,
                    allotted_teacher=tutor,
                    timeslot__day_of_week=day_schedule.day
                ).order_by('timeslot__period')
                
                # Organize lessons by period
                day_sessions = [[] for _ in range(day_schedule.teaching_slots)]
                
                for lesson in lessons:
                    period_index = lesson.timeslot.period - 1
                    lesson_info = {
                        "subject": abbreviate(lesson.course.subject.name),
                        "is_elective": lesson.is_elective,
                        "room_no": lesson.classroom_assignment.room.room_number if lesson.classroom_assignment else None
                    }
                    day_sessions[period_index].append(lesson_info)
                
                # Only add days with sessions
                teacher_entry["timetable_rows"][day_schedule.day] = day_sessions
            
            # Only add teachers with at least one lesson
            if teacher_entry["timetable_rows"]:
                condensed_timetable.append(teacher_entry)
    
    return  condensed_timetable



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def default_student_week_timetable_condensed_view(request):
    """
    Function-based view to fetch default weekly timetable for a teacher
    using REST Framework decorators
    """
    
    user = request.user

    try:
        # Retrieve the active timetable for the current user/institution
        timetable = Timetable.objects.filter(school=user, is_default=True).first()


        if not timetable:
            return Response({
                'error': 'No active timetable found',
                'message': 'There is no active timetable for your institution.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Generate condensed timetable
        condensed_student_timetable = get_student_condensed_timetable( timetable)
        condensed_teacher_timetable = get_teacher_condensed_timetable( timetable)
        
        week_period_timing = {}

        # Iterate through each schedule to gather periods
        for schedule in timetable.day_schedules.all():
            periods = []  # Initialize the periods list
            
            # For each period in the day's schedule, gather the start and end times
            for period_number in range(1, schedule.teaching_slots + 1):
                period = schedule.periods.filter(period_number=period_number).first()
                
                periods.append({
                    'period': period_number,
                    'start_time': period.start_time if period else None,
                    'end_time': period.end_time if period else None
                })
            
            # Store the periods for the day in the week_period_timing dictionary
            week_period_timing[schedule.day] = periods

        # Now, create the weekly_schedule_header using the populated week_period_timing
        weekly_schedule_header = [
            {
                "day": schedule.day,
                "teaching_slots": schedule.teaching_slots,
                "day_name": dict(DayChoices.choices).get(schedule.day),  # Ensure this maps correctly
                "periods": week_period_timing.get(schedule.day, [])  # Safe access with default empty list if not found
            }
            for schedule in timetable.day_schedules.all()
        ]

        # Now weekly_schedule_header should contain the desired data with periods


        return Response({
            'timetable': {"weekly_schedule_header":weekly_schedule_header,"condensed_teacher_timetable":condensed_teacher_timetable,"condensed_student_timetable":condensed_student_timetable},
            'message': 'Timetable retrieved successfully'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': str(e),
            'message': 'An unexpected error occurred while fetching timetable'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
        
