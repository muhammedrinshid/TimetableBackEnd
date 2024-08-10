from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from ...optapy_solver.solver import run_optimization
from ...time_table_models import Timetable, StandardLevel, ClassSection, Course, Tutor, ClassroomAssignment, Timeslot, Lesson
from django.db import transaction

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














def save_optimization_results(user, optimization_result):
    try:
        with transaction.atomic():
            # Create Timetable
            timetable = Timetable.objects.create(
                name=f"Timetable_{user.username}_{Timetable.objects.filter(school=user).count() + 1}",
                school=user,
                score=getattr(optimization_result, 'score', None),
                optimal=getattr(optimization_result, 'optimal', False),
                feasible=getattr(optimization_result, 'feasible', False)
            )

            # Process StandardLevels
            for standard_data in getattr(optimization_result, 'standard_levels', []):
                StandardLevel.objects.get_or_create(
                    standard_id=standard_data.id,
                    timetable=timetable,
                    school=user,
                    defaults={'name': getattr(standard_data, 'short_name', f"Standard_{standard_data.id}")}
                )

            # Process ClassSections
            for class_data in getattr(optimization_result, 'class_sections', []):
                standard = StandardLevel.objects.get(standard_id=class_data.standard.id, timetable=timetable)
                ClassSection.objects.get_or_create(
                    classroom_id=class_data.id,
                    timetable=timetable,
                    school=user,
                    defaults={
                        'standard': standard,
                        'division': getattr(class_data, 'division', 'A'),
                        'name': getattr(class_data, 'name', f"Class_{class_data.id}")
                    }
                )

            # Process Courses
            for course_data in getattr(optimization_result, 'courses', []):
                Course.objects.get_or_create(
                    subject_id=course_data.id,
                    timetable=timetable,
                    school=user,
                    defaults={'name': getattr(course_data, 'name', f"Course_{course_data.id}")}
                )

            # Process Tutors
            for tutor_data in getattr(optimization_result, 'tutors', []):
                Tutor.objects.get_or_create(
                    teacher_id=tutor_data.id,
                    timetable=timetable,
                    school=user,
                    defaults={'name': getattr(tutor_data, 'name', f"Tutor_{tutor_data.id}")}
                )

            # Process ClassroomAssignments
            for room_data in getattr(optimization_result, 'rooms', []):
                ClassroomAssignment.objects.get_or_create(
                    room_id=room_data.id,
                    timetable=timetable,
                    school=user,
                    defaults={
                        'name': getattr(room_data, 'name', f"Room_{room_data.id}"),
                        'capacity': getattr(room_data, 'capacity', 30),
                        'room_type': getattr(room_data, 'room_type', 'Standard'),
                        'occupied': getattr(room_data, 'occupied', False)
                    }
                )

            # Process Timeslots
            for timeslot_data in getattr(optimization_result, 'timeslots', []):
                Timeslot.objects.get_or_create(
                    day_of_week=timeslot_data.day_of_week,
                    period=timeslot_data.period,
                    timetable=timetable,
                    school=user
                )

            # Process Lessons
            for lesson_data in getattr(optimization_result, 'lessons', []):
                course = Course.objects.get(subject_id=lesson_data.subject.id, timetable=timetable)
                class_section = ClassSection.objects.get(classroom_id=lesson_data.class_section.id, timetable=timetable)
                alotted_teacher = Tutor.objects.get(teacher_id=lesson_data.alotted_teacher.id, timetable=timetable)
                classroom_assignment = ClassroomAssignment.objects.get(room_id=lesson_data.room.id, timetable=timetable)
                timeslot = Timeslot.objects.get(
                    day_of_week=lesson_data.timeslot.day_of_week,
                    period=lesson_data.timeslot.period,
                    timetable=timetable
                )

                Lesson.objects.create(
                    timetable=timetable,
                    school=user,
                    course=course,
                    alotted_teacher=alotted_teacher,
                    class_section=class_section,
                    classroom_assignment=classroom_assignment,
                    timeslot=timeslot
                )

            return timetable

    except Exception as e:
        # Log the error or handle it as appropriate for your application
        print(f"Error saving optimization results: {str(e)}")
        raise