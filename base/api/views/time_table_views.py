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
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo





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
                lesson_instance = Lesson.objects.create(
                    timetable=timetable,
                    school=user,
                    course=course,
                    allotted_teacher=tutor,
                    classroom_assignment=classroom_assignment,
                    timeslot=timeslot_obj,
                    elective_subject_name=lesson.elective_subject_name,
                    is_elective=lesson.is_elective
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
                allotted_teacher=tutor,
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
def get_whole_teacher_default_week_timetable(request):
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whole_teacher_week_timetable(request, pk):
    user = request.user
    
    # Check if pk is provided
    if pk is None:
        return Response({"error": "Timetable ID is required"}, status=400)
    
    try:
        # Get the timetable instance
        timetable = Timetable.objects.get(school=user, id=pk)
    except Timetable.DoesNotExist:
        return Response({"error": "Timetable not found"}, status=404)
    except Exception as e:
        return Response({"error": "Internal Server Error"}, status=500)
    
    # Get working days for the user
    working_days = user.working_days
    
    # Initialize week timetable
    week_timetable = {day: get_teacher_day_timetable(user, timetable, day) for day in working_days}
    
    # Serialize the week timetable
    serializer = WholeTeacherWeekTimetableSerializer(week_timetable, working_days=working_days)
    
    # Return the response
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
def get_whole_student_default_week_timetable(request):
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
def get_whole_student_week_timetable(request, pk):
    user = request.user
    
    # Check if pk is provided
    if pk is None:
        return Response({"error": "Timetable ID is required"}, status=400)
    
    # Get the timetable instance
    try:
        timetable = Timetable.objects.get(school=user, id=pk)
    except Timetable.DoesNotExist:
        return Response({"error": "Timetable not found"}, status=404)
    
    # Get working days for the user
    working_days = user.working_days
    
    # Initialize week timetable
    week_timetable = {}
    
    # Iterate over working days
    for day_code in working_days:
        day_timetable = get_student_day_timetable(user, timetable, day_code)
        week_timetable[day_code] = day_timetable
    
    # Serialize the week timetable
    serializer = StudentWeekTimetableSerializer(week_timetable, working_days=working_days)
    
    # Return the response
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
            'course', 'allotted_teacher__teacher', 'classroom_assignment__room', 'timeslot'
        
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
            allotted_teacher=tutor,
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



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_classroom_timetable(request, pk):
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)

    try:
        classroom = Classroom.objects.get(id=pk, school=user)
        classsection = ClassSection.objects.get(classroom=classroom, timetable=timetable)
    except Classroom.DoesNotExist:
        return Response({'error': 'No classroom found for this school.'}, status=404)
    except ClassSection.DoesNotExist:
        return Response({'error': 'No classroom found for this timetable.'}, status=422)

    working_days = user.working_days
    day_timetable = []

    for day_code in working_days:
        day_lessons = Lesson.objects.filter(
            timetable=timetable,
            timeslot__day_of_week=day_code,
            class_sections__in=[classsection]
        ).select_related(
            'course', 'allotted_teacher__teacher', 'classroom_assignment__room', 'timeslot'
        )
        
        sessions = defaultdict(list)
        for lesson in day_lessons:
            sessions[lesson.timeslot.period - 1].append(lesson)

        formatted_sessions = [sessions[i] for i in range(timetable.number_of_lessons)]

        day_timetable.append({
            'day': day_code,
            'sessions': formatted_sessions
        })

    serializer = ClassroomWeekTimetableSerializer(day_timetable, many=True, context={'class_section': classsection})
    timetable_data = serializer.data

    # Create a new workbook and select the active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = f"{classroom.standard.short_name}-{classroom.division} Timetable"

    # Define styles
    header_fill = PatternFill(start_color="4285F4", end_color="4285F4", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    bold_font = Font(bold=True, size=12)
    normal_font = Font(size=11)
    elective_fill = PatternFill(start_color="FFFACD", end_color="FFFACD", fill_type="solid")  # light yellow
    core_fill = PatternFill(start_color="E0FFFF", end_color="E0FFFF", fill_type="solid")  # light cyan

    # Write headers
    headers = ['Day'] + [f'Session {i+1}' for i in range(len(timetable_data[0]['sessions']))]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(color="FFFFFF", bold=True, size=14)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # Write timetable data
    for row, day_data in enumerate(timetable_data, start=2):
        day_cell = ws.cell(row=row, column=1, value=day_data['day'])
        day_cell.border = border
        day_cell.font = Font(bold=True, size=12)
        day_cell.alignment = Alignment(horizontal='center', vertical='center')

        for col, session in enumerate(day_data['sessions'], start=2):
            if session:
                subject = session['name']
                session_type = session['type']
                for distribution in session['class_distribution']:
                    teacher = distribution['teacher']['name']
                    room = f"{distribution['room']['name']} ({distribution['room']['number']})"

                    # Style elective vs. core subjects differently
                    if session_type == 'Elective':
                        students = distribution['number_of_students_from_this_class']
                        session_info = f"Subject: {subject} (Elective)\nTeacher: {teacher}\nRoom: {room}\nStudents: {students}"
                        cell_fill = elective_fill
                    else:
                        session_info = f"Subject: {subject} (Core)\nTeacher: {teacher}\nRoom: {room}"
                        cell_fill = core_fill

                    # Create and style the cell for this session
                    cell = ws.cell(row=row, column=col, value=f"\n{session_info}\n")
                    cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
                    cell.border = border
                    cell.fill = cell_fill

                    # Apply different styles to different parts of the content
                    lines = cell.value.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('Subject:'):
                            lines[i] = f"$BOLD_BLUE${line}$ENDBOLD_BLUE$"
                        elif line.startswith('Teacher:'):
                            lines[i] = f"$BOLD_GREEN${line}$ENDBOLD_GREEN$"
                        elif line.startswith('Room:'):
                            lines[i] = f"$RED${line}$ENDRED$"
                        elif line.startswith('Students:'):
                            lines[i] = f"$INDIGO${line}$ENDINDIGO$"
                    
                    cell.value = "\n".join(lines)

    # Adjust column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 30  # Increased width for better spacing

    # Adjust row height to fit content
    for row in range(1, len(timetable_data) + 2):
        ws.row_dimensions[row].height = 100  # Increased height for better spacing

    # Apply rich text formatting
    for row in ws.iter_rows(min_row=2, max_row=len(timetable_data) + 1, min_col=2):
        for cell in row:
            if cell.value:
                parts = []
                current_text = ""
                current_format = None
                for part in cell.value.split('$'):
                    if part == 'BOLD_BLUE':
                        if current_text:
                            parts.append((current_text, current_format))
                        current_format = Font(bold=True, size=12, color="000080")
                        current_text = ""
                    elif part == 'ENDBOLD_BLUE':
                        parts.append((current_text, current_format))
                        current_format = None
                        current_text = ""
                    elif part == 'BOLD_GREEN':
                        if current_text:
                            parts.append((current_text, current_format))
                        current_format = Font(bold=True, size=11, color="006400")
                        current_text = ""
                    elif part == 'ENDBOLD_GREEN':
                        parts.append((current_text, current_format))
                        current_format = None
                        current_text = ""
                    elif part == 'RED':
                        if current_text:
                            parts.append((current_text, current_format))
                        current_format = Font(size=11, color="8B0000")
                        current_text = ""
                    elif part == 'ENDRED':
                        parts.append((current_text, current_format))
                        current_format = None
                        current_text = ""
                    elif part == 'INDIGO':
                        if current_text:
                            parts.append((current_text, current_format))
                        current_format = Font(size=11, color="4B0082")
                        current_text = ""
                    elif part == 'ENDINDIGO':
                        parts.append((current_text, current_format))
                        current_format = None
                        current_text = ""
                    else:
                        current_text += part
                if current_text:
                    parts.append((current_text, current_format))
                
                cell.value = parts[0][0]
                cell.font = parts[0][1] or Font(size=11)
                for text, font in parts[1:]:
                    if font:
                        cell.font = font
                    cell.value += text

    # Create the HTTP response with the Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{classroom.standard.short_name}-{classroom.division}_timetable.xlsx"'
    wb.save(response)

    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_teacher_timetable(request, pk=None):
    user = request.user
    timetable = get_object_or_404(Timetable, school=user, is_default=True)

    if pk is not None:
        try:
            teacher = Teacher.objects.get(id=pk, school=user)
            tutor = Tutor.objects.get(teacher=teacher, timetable=timetable)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found for this school.'}, status=status.HTTP_404_NOT_FOUND)
        except Tutor.DoesNotExist:
            return Response({'error': 'No timetable available for this teacher.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    working_days = user.working_days
    day_timetable = []

    for day_code in working_days:
        sessions = [None] * timetable.number_of_lessons
        lessons = Lesson.objects.filter(
            timetable=timetable,
            allotted_teacher=tutor,
            timeslot__day_of_week=day_code
        ).order_by('timeslot__period')

        for lesson in lessons:
            sessions[lesson.timeslot.period - 1] = lesson

        if sessions:
            day_timetable.append({
                'day': day_code,
                'sessions': sessions
            })

    serializer = TeacherWeekTimetableSerializer(day_timetable, many=True)
    timetable_data = serializer.data

    # Create a new workbook and select the active sheet
    wb = Workbook()
    ws = wb.active
    ws.title = f"{teacher.name}'s Timetable"

    # Define styles
    header_font = Font(name='Arial', bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    day_font = Font(name='Arial', bold=True, size=11)
    content_font = Font(name='Arial', size=10)
    centered_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Color mapping for session types
    color_map = {
        'Core': PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),  # Light green
        'Elective': PatternFill(start_color="E2EFFF", end_color="E2EFFF", fill_type="solid"),  # Light blue
        'Free': PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")  # Light yellow
    }
    day_fill = PatternFill(start_color="008080", end_color="66CDAA", fill_type="solid")  # Teal to light teal

    # Define the alignment (centered both vertically and horizontally)
    day_alignment = Alignment(horizontal='center', vertical='center')
    # Write headers
    headers = ["Day"] + [f"Session {i+1}" for i in range(timetable.number_of_lessons)]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = centered_alignment
        cell.border = border

    # Write timetable data
    for row, day_data in enumerate(timetable_data, start=2):
        cell = ws.cell(row=row, column=1, value=day_data['day'])
        cell.font = day_font
        cell.fill = day_fill  # Set the background color
        cell.alignment = day_alignment
            
        for col, session in enumerate(day_data['sessions'], start=2):
            cell = ws.cell(row=row, column=col)
            if session['subject']:
                cell_value = f"{session['subject'] or session['elective_subject_name']}\n"
                cell_value += f"Room: {session['room']['room_number'] if session['room'] else 'N/A'}\n"
                if session['class_details']: 
                    for class_detail in session['class_details']:
                        cell_value += f"{class_detail['standard']} {class_detail['division']}"
                        if session['type'] == 'Elective':
                            cell_value += f" ({class_detail['number_of_students']} students)"
                        cell_value += "\n"
                cell.value = cell_value.strip()
                if session['type']: 

                    cell.fill = color_map[session['type']]
            else:
                cell.value = "Free Period/\nPlanning Period"
                cell.fill = color_map['Free']
            
            cell.font = content_font
            cell.alignment = centered_alignment
            cell.border = border

    # Adjust column widths and row heights
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20
    
    for row in range(1, len(timetable_data) + 2):  # +2 to include header row
        ws.row_dimensions[row].height = 80  # Adjust this value as needed

    # Create the HTTP response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{teacher.name}_timetable.xlsx"'

    # Save the workbook to the response
    wb.save(response)

    return response