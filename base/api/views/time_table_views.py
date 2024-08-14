from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from ...optapy_solver.solver import run_optimization
from ...time_table_models import Timetable, StandardLevel, ClassSection, Course, Tutor, ClassroomAssignment, Timeslot, Lesson,LessonClassSection
from django.db import transaction

from ..serializer.time_table_serializer import TimetableSerializer,TimetableUpdateSerializer
from collections import defaultdict

from django.db import transaction

from django.db import transaction

def save_optimization_results(user, solution):
    try:
        with transaction.atomic():
            # Create Timetable
            score = solution.get_score()
            timetable = Timetable.objects.create(
                name=f"Timetable_{user.username}_{Timetable.objects.filter(school=user).count() + 1}",
                school=user,
            )

            for lesson in solution.get_lesson_list():
                # Process Course
                course, _ = Course.objects.get_or_create(
                    subject_id=lesson.subject.id,
                    timetable=timetable,
                    school=user,
                    defaults={'name': lesson.subject.name}
                )

                # Process Tutor
                tutor, _ = Tutor.objects.get_or_create(
                    teacher_id=lesson.alotted_teacher.id,
                    timetable=timetable,
                    school=user,
                    defaults={'name': lesson.alotted_teacher.name}
                )

                # Process ClassroomAssignment
                room = lesson.get_room()
                if room:
                    classroom_assignment, _ = ClassroomAssignment.objects.get_or_create(
                        room_id=room.id,
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
                    timeslot=timeslot_obj
                )

                # Process ClassSection
                for class_section in lesson.class_sections:
                    standard, _ = StandardLevel.objects.get_or_create(
                        name=class_section.standard.short_name,
                        timetable=timetable,
                        school=user,
                        standard_id=class_section.standard.id
                    )

                    class_section_obj, _ = ClassSection.objects.get_or_create(
                        classroom_id=class_section.id,
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
                    number_of_students = students_distribution.get(class_section.id, 0)

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
    
    
    optimization_result = run_optimization(request=request)
    try:
        timetable = save_optimization_results(request.user, optimization_result)
        # serializer = TimetableSerializer(timetable)
        return Response({
            "message": "Timetable optimization completed and saved",
            # "timetable": serializer.data
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
        "all_classes_subject_assigned_atleast_one_teacher": user.all_classes_subject_assigned_atleast_one_teacher
    }

    reasons = []

    if not user.all_class_subjects_have_correct_elective_groups:
        reasons.append("Not all class subjects have correct elective groups.")
    
    if not user.all_classes_assigned_subjects:
        reasons.append("Not all classes have assigned subjects.")
    
    if not user.all_classes_subject_assigned_atleast_one_teacher:
        reasons.append("Not all class subjects have at least one assigned teacher.")

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


