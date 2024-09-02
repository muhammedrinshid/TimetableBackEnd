from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from ...optapy_solver.solver import run_optimization
from ...time_table_models import Timetable, StandardLevel, ClassSection, Course, Tutor, ClassroomAssignment, Timeslot, Lesson,LessonClassSection
from django.db import transaction

from django.db.models import Prefetch
from ..serializer.time_table_serializer import TimetableSerializer,TimetableUpdateSerializer
from collections import defaultdict

from rest_framework.decorators import api_view
from rest_framework.response import Response
from ...models import  Teacher, Subject, Room,Classroom,Standard
from ..serializer.time_table_serializer import TeacherDayTimetableSerializer,StudentWeekTimetableSerializer,StudentDayTimetableSerializer,WholeTeacherWeekTimetableSerializer,TeacherWeekTimetableSerializer,ClassroomWeekTimetableSerializer
from django.shortcuts import get_object_or_404








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
def save_optimization_results(user, solution):
    try:
        with transaction.atomic():
            # Create Timetable
            score = solution.get_score()
            number_of_lessons = (user.teaching_slots)

            timetable = Timetable.objects.create(
                name=f"Timetable_{user.username}_{Timetable.objects.filter(school=user).count() + 1}",
                school=user,
                number_of_lessons=number_of_lessons,
            )

            for lesson in solution.get_lesson_list():
                # Process Course
                subject=Subject.objects.get(id=lesson.subject.id)
                course, _ = Course.objects.get_or_create(
                    subject=subject,
                    timetable=timetable,
                    school=user,
                    defaults={'name': lesson.subject.name}
                )

                # Process Tutor
                teacher=Teacher.objects.get(id=lesson.alotted_teacher.id)
                tutor, _ = Tutor.objects.get_or_create(
                    teacher=teacher,
                    timetable=timetable,
                    school=user,
                    defaults={'name': lesson.alotted_teacher.name}
                )

                # Process ClassroomAssignment
                room = lesson.get_alotted_room()
                if room:
                    room=Room.objects.get(id=room.id)
                    classroom_assignment, _ = ClassroomAssignment.objects.get_or_create(
                        room=room,
                        timetable=timetable,
                        school=user,
                        defaults={
                            'name': room.name,
                            'capacity': getattr(room, 'capacity', 30),
                            'room_type': getattr(room, 'room_type', 'Standard'),
                            'occupied': getattr(room, 'occupied', False)
                        }
                    )
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
                lesson_instance = Lesson.objects.create(
                    timetable=timetable,
                    school=user,
                    course=course,
                    alotted_teacher=tutor,
                    classroom_assignment=classroom_assignment,
                    timeslot=timeslot_obj,
                    elective_subject_name=lesson.elective_subject_name,
                    is_elective=lesson.is_elective
                )

                # Process ClassSection
                for class_section in lesson.class_sections:
                    std=Standard.objects.get(id=class_section.standard.id)
                    standard, _ = StandardLevel.objects.get_or_create(
                        name=class_section.standard.short_name,
                        timetable=timetable,
                        school=user,
                        standard=std
                    )
                    classroom=Classroom.objects.get(id=class_section.id)
                    class_section_obj, _ = ClassSection.objects.get_or_create(
                        classroom=classroom,
                        timetable=timetable,
                        school=user,
                        defaults={
                            'standard': standard,
                            'division': class_section.division,
                            'name': class_section.name
                        }
                    )

                    # Get number of students from the lesson's students_distribution
                    # Ensure students_distribution is not None
                    students_distribution = lesson.students_distribution or {}
                    number_of_students = students_distribution.get(str(class_section.id), 0)


                    # Create LessonClassSection relationship
                    LessonClassSection.objects.create(
                        lesson=lesson_instance,  # Use the created Lesson instance
                        class_section=class_section_obj,
                        number_of_students=number_of_students
                    )

            return timetable

    except Exception as e:
        # Log the error or handle it as appropriate for your application
        print(f"Error saving optimization results: {str(e)}")
        raise








@api_view(['GET'])
@permission_classes([IsAuthenticated])
def run_module_view(request):
    # Run the optimization process
    optimization_result = run_optimization(request=request)
    # print(optimization_result)
    # Access the score
    score = optimization_result.get_score()  # or use optimization_result.score

    # Check if score indicates any hard constraint violations
    # Assuming score is an object or string that includes information on hard constraint violations
    hard_constraints_violated = score.hard_constraint_violations == 0 if hasattr(score, 'hard_constraint_violations') else parse_hard_violations_from_score(score)

    if hard_constraints_violated == 0:
        
        try:
            # Save the optimization results
            timetable = save_optimization_results(request.user, optimization_result)
            serializer = TimetableSerializer(timetable)
            return Response({
                "message": "Timetable optimization completed and saved",
                # "timetable": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": "Error saving optimization results",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        # Return an error if there are hard constraint violations
        return Response({
            "message": "Optimization failed due to hard constraint violations",
            "violations": hard_constraints_violated
        }, status=status.HTTP_400_BAD_REQUEST)
        
        
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_class_subjects(request):
    user = request.user

    results = {
        "all_class_subjects_have_correct_elective_groups": user.all_class_subjects_have_correct_elective_groups,
        "all_classes_assigned_subjects": user.all_classes_assigned_subjects,
        "all_classes_subject_assigned_atleast_one_teacher": user.all_classes_subject_assigned_atleast_one_teacher,
        "all_classrooms_have_rooms": user.all_classrooms_have_rooms,
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
def get_teacher_day_timetable(user, timetable, day_of_week):
    # Get all teachers for the school
    teachers = Teacher.objects.filter(school=user)
    
    day_timetable = []
    
    for teacher in teachers:
        # Check if there's a Tutor object for this teacher and timetable
        tutor = Tutor.objects.filter(teacher=teacher, timetable=timetable).first()
        
        if tutor:
            # Initialize sessions with None for each period
            sessions = [None] * timetable.number_of_lessons
            
            # Get all lessons for this tutor on the specified day
            lessons = Lesson.objects.filter(
                timetable=timetable,
                alotted_teacher=tutor,
                timeslot__day_of_week=day_of_week
            ).order_by('timeslot__period')
            # Fill in the sessions with actual lesson data
            for lesson in lessons:
                sessions[lesson.timeslot.period - 1] = lesson
            
            # Remove any remaining None values
            # sessions = [s for s in sessions if s is not None]
            if sessions:  # Only add to day_timetable if there are sessions
                day_timetable.append({
                    'instructor': tutor,
                    'sessions': sessions
                })
    
    return day_timetable

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_teacher_single_day_timetable(request, day_of_week):
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)
    day_timetable = get_teacher_day_timetable(user, timetable, day_of_week)
    
    serializer = TeacherDayTimetableSerializer(day_timetable, many=True)
    serialized_data = serializer.data  # Access serialized data

    # Modify serialized data
    for data in serialized_data:
        if "instructor" in data:
            data["instructor"]["present"] = [True] * user.teaching_slots

    return Response(serialized_data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whole_teacher_week_timetable(request):
    user = request.user

    timetable = get_object_or_404(Timetable, school=user, is_default=True)
    
    # Get working days
    working_days = user.working_days

    week_timetable = {}
    for day_code in working_days:
        day_name =day_code
        day_timetable = get_teacher_day_timetable(user, timetable, day_name)
        week_timetable[day_code] = day_timetable
    
    serializer = WholeTeacherWeekTimetableSerializer(week_timetable, working_days=working_days)
    return Response(serializer.data)




















def get_student_day_timetable(user, timetable, day_of_week):
    class_sections = ClassSection.objects.filter(
        timetable=timetable
    ).select_related(
        'classroom__standard', 'classroom__room'
    ).prefetch_related(
        Prefetch(
            'lessons',
            queryset=Lesson.objects.filter(
                timetable=timetable,
                timeslot__day_of_week=day_of_week
            ).select_related(
                'course', 'alotted_teacher__teacher', 'classroom_assignment__room', 'timeslot'
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
        sessions = defaultdict(list)
        for lesson in class_section.day_lessons:
            sessions[lesson.timeslot.period - 1].append(lesson)

        formatted_sessions = [sessions[i] for i in range(timetable.number_of_lessons)]

        day_timetable.append({
            'classroom': class_section,
            'sessions': formatted_sessions
        })

    return day_timetable


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_single_day_timetable(request, day_of_week):
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)
    day_timetable = get_student_day_timetable(user, timetable, day_of_week)
    
    serializer = StudentDayTimetableSerializer(day_timetable, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_week_timetable(request):
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)
    
    working_days = user.working_days

    week_timetable = {}
    for day_code in working_days:
        day_timetable = get_student_day_timetable(user, timetable, day_code)
        week_timetable[day_code] = day_timetable
    
    serializer = StudentWeekTimetableSerializer(week_timetable, working_days=working_days)
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_classroom_week_timetable(request,pk):
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)

    if pk is not None:
        try:
            classroom=Classroom.objects.get(id=pk,school=user)
            classsection=ClassSection.objects.get(classroom=classroom,timetable=timetable)
            
        except Classroom.DoesNotExist:
            return Response({'error': 'No classroom found for this school.'}, status=status.HTTP_404_NOT_FOUND)
        except  ClassSection.DoesNotExist:
            
            return Response({'error': 'No classroom found for this school.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    working_days = user.working_days

    day_timetable = []
    
    
    
    
    for day_code in working_days:
        day_lessons = Lesson.objects.filter(
            timetable=timetable,
            timeslot__day_of_week=day_code,
            class_sections__in=[classsection]
        ).select_related(
            'course', 'alotted_teacher__teacher', 'classroom_assignment__room', 'timeslot'
        
    )
        
        sessions = defaultdict(list)
        for lesson in day_lessons:
            sessions[lesson.timeslot.period - 1].append(lesson)

        formatted_sessions = [sessions[i] for i in range(timetable.number_of_lessons)]

            
        

        day_timetable.append({
            'day': day_code,
            'sessions': formatted_sessions
        })
    serializer = ClassroomWeekTimetableSerializer(day_timetable,many=True,context={'class_section': classsection})
    return Response(serializer.data)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_teacher_week_timetable(request,pk):
    # Get all teachers for the school
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)

    if pk is not None:
        try:
            teacher=Teacher.objects.get(id=pk,school=user)
            tutor=Tutor.objects.get(teacher=teacher,timetable=timetable)
            
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found for this school.'}, status=status.HTTP_404_NOT_FOUND)
        except Tutor.DoesNotExist:
             return Response({'error': 'No timetable available for this teacher.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        


    working_days = user.working_days

    day_timetable = []
    
    
    for day_code in working_days:
        # Check if there's a Tutor object for this teacher and timetable
        
        # Initialize sessions with None for each period
        sessions = [None] * timetable.number_of_lessons
        
        # Get all lessons for this tutor on the specified day
        lessons = Lesson.objects.filter(
            timetable=timetable,
            alotted_teacher=tutor,
            timeslot__day_of_week=day_code
        ).order_by('timeslot__period')
        # Fill in the sessions with actual lesson data
        for lesson in lessons:
            sessions[lesson.timeslot.period - 1] = lesson
        
        # Remove any remaining None values
        # sessions = [s for s in sessions if s is not None]
        if sessions:  # Only add to day_timetable if there are sessions
            day_timetable.append({
                'day': day_code,
                'sessions': sessions
            })
    
    serializer = TeacherWeekTimetableSerializer(day_timetable,many=True)
    return Response(serializer.data)






