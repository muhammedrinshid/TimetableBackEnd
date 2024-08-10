from .domain import TimeTable
from .domain import Timeslot,Lesson,ClassSection,StandardLevel,TutorManager,CourseManager,ClassroomAssignmentManager
import uuid

import optapy.config
from optapy.types import Duration
from optapy import solver_factory_create
from .constraints import define_constraints



def print_timetable(solution):
    for lesson in solution.get_lesson_list():
        print(f"Lesson: {lesson.subject}, Teacher: {lesson.alotted_teacher.name}, "
              f"Room: {lesson.get_room().name if lesson.get_room() else 'Not assigned'}, "
              f"Timeslot: {lesson.get_timeslot().day_of_week} - Period {lesson.get_timeslot().period}"
              f"Timeslot: {lesson.class_section}"
              )

def run_optimization(request):
    # Here you would collect data from your Django models and create the problem instance
    problem = create_problem_from_django_models(request.user)
    solver_config = optapy.config.solver.SolverConfig() \
    .withEntityClasses(Lesson) \
    .withSolutionClass(TimeTable) \
    .withConstraintProviderClass(define_constraints) \
    .withTerminationSpentLimit(Duration.ofSeconds(10))

    solution = solver_factory_create(solver_config) \
        .buildSolver() \
        .solve(problem)

    # print_timetable(solution)
    return solution
def create_problem_from_django_models(user):
    from ..models import User, Room, Grade, Standard, Classroom, ClassSubject, ClassSubjectSubject, Teacher
    school = user  # Replace with actual school ID
    rooms = [ClassroomAssignmentManager.get_or_create(id=room.id,name= room.name,capacity=room.capacity,room_type=room.room_type,occupied=room.occupied) for room in Room.objects.filter(school=school)]
    # teachers=[TutorManager.get_or_create(id=teacher.id,name=teacher.name) for teacher in Teacher.objects.filter(school=school)]
    working_days = school.working_days
    teaching_slots = school.teaching_slots
    timeslots = [
        Timeslot(f"{day}-{period}", day, period)
        for day in working_days
        for period in range(1, teaching_slots + 1)
    ]
    
    lessons = []
    for grade in Grade.objects.filter(school=school):
        for standard in Standard.objects.filter(grade=grade,school=school):
            standard_obj=StandardLevel(id=standard.id,short_name=standard.short_name)
            
            for classroom in Classroom.objects.filter(standard=standard):
                classroom_obj=ClassSection(
                    id=classroom.id,standard=standard_obj,division=classroom.division,name=classroom.name
                )
                room=classroom.room
                room_obj=None
                if room is not None:
                    room_obj=ClassroomAssignmentManager.get_or_create(id=room.id,name=room.name,capacity=room.capacity,room_type=room.room_type,occupied=room.occupied)
                    
                for class_subject in ClassSubject.objects.filter(class_room=classroom):
                    if class_subject.be_included_in_first_selection:
                        subject = class_subject.subjects.first()
                        subject_obj=CourseManager.get_or_create(id=subject.id,name=subject.name)
                        class_subject_subject = ClassSubjectSubject.objects.get(class_subject=class_subject, subject=subject)
                        available_teachers=[TutorManager.get_or_create(id=teacher.id,name=teacher.name) for teacher in class_subject_subject.assigned_teachers.all()]
                        
                        for _ in range(class_subject.lessons_per_week):
                            lesson = Lesson(
                                id=str(uuid.uuid4()),
                                subject=subject_obj,
                                available_teachers=available_teachers,
                                class_section=classroom_obj,
                                room=room_obj
                                
                            )
                            lessons.append(lesson)
    return TimeTable(timeslot_list=timeslots, room_list=rooms, lesson_list=lessons )