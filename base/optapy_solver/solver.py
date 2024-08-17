from .domain import TimeTable
from .domain import Timeslot,Lesson,ClassSection,StandardLevelManager,TutorManager,CourseManager,ClassroomAssignmentManager,ClassSectionManager
import uuid
from .solver_helper_functions import create_core_lesson_ojbects,create_elective_lesson_ojbects,get_all_elective_group_of_user,create_elective_lesson_data
import optapy.config
from optapy.types import Duration
from optapy import solver_factory_create
from .constraints import define_constraints



def print_timetable(solution):
    for lesson in solution.get_lesson_list():
        print(f"Lesson: {lesson.subject}, Teacher: {lesson.alotted_teacher.name}, "
              f"Room: {lesson.get_room().name if lesson.get_room() else 'Not assigned'}, "
              f"Timeslot: {lesson.get_timeslot().day_of_week} - Period {lesson.get_timeslot().period}"
              f"Timeslot: {lesson.class_sections}"
              )

def run_optimization(request):
    # Here you would collect data from your Django models and create the problem instance
    problem = create_problem_from_django_models(request.user)
    solver_config = optapy.config.solver.SolverConfig() \
    .withEntityClasses(Lesson) \
    .withSolutionClass(TimeTable) \
    .withConstraintProviderClass(define_constraints) \
    .withTerminationSpentLimit(Duration.ofSeconds(150))

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
    all_elective_group_of_school=get_all_elective_group_of_user(school)
    rough_data_for_elective_lesson_creation=create_elective_lesson_data(all_elective_group_of_school)
    
    
    lessons = create_elective_lesson_ojbects(data=rough_data_for_elective_lesson_creation,school=school) + create_core_lesson_ojbects(school=school)
    debug=lessons[0]
    attributes = vars(debug)
    for attr_name, attr_value in attributes.items():
       print(f"Name: {attr_name}, Value: {attr_value}, Type: {type(attr_value).__name__}")
    return TimeTable(timeslot_list=timeslots, room_list=rooms, lesson_list=lessons )