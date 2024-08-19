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
    .withTerminationSpentLimit(Duration.ofSeconds(10))

    solution = solver_factory_create(solver_config) \
        .buildSolver() \
        .solve(problem)

    # print_timetable(solution)
    return solution
def create_problem_from_django_models(user):
    from ..models import User, Room, Grade, Standard, Classroom, ClassSubject, ClassSubjectSubject, Teacher
    school = user 
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
    # for attr_name, attr_value in attributes.items():
    #    print(f"Name: {attr_name}, Value: {attr_value}, Type: {type(attr_value).__name__}")
    return TimeTable(timeslot_list=timeslots, room_list=rooms, lesson_list=lessons )
















[{'grp_id': 'ddee07aa-c463-4dfe-81bc-57eb8841760a', 'subjectDistributionData': {'6b669d88-8234-460a-8678-ab8ee842f642': {'total_students': 40, 'class_rooms': [{'id': '75378b2d-6d10-4b5b-a7a2-4ed78c99a733', 'students_from_this_division': 15}, {'id': '11c67b74-a98a-418f-b97b-fc4a4fa6201f', 'students_from_this_division': 25}], 'available_teachers': ['cb1e3391-95c5-4168-ac96-a32948f37781']}, '8354271d-4522-46c6-a585-ed3b4457d2ba': {'total_students': 40, 'class_rooms': [{'id': '75378b2d-6d10-4b5b-a7a2-4ed78c99a733', 'students_from_this_division': 25}, {'id': '11c67b74-a98a-418f-b97b-fc4a4fa6201f', 'students_from_this_division': 15}], 'available_teachers': ['39b22a3e-933c-4d49-9b18-4ea7dfbc2423']}}, 'lessons_per_week': 2, 'elective_subject_name': 'Life Skills'}, {'grp_id': '0611a2bd-e30e-4deb-80a6-85d0526bb4b2', 'subjectDistributionData': {'27528d28-c8ce-4300-9ddd-5edc19c45e78': {'total_students': 10, 'class_rooms': [{'id': '75378b2d-6d10-4b5b-a7a2-4ed78c99a733', 'students_from_this_division': 10}], 'available_teachers': ['549b588a-5ca0-4f45-9865-db23dc824ca2', '39b22a3e-933c-4d49-9b18-4ea7dfbc2423']}, '5879cb19-3f56-46bf-b4e9-164139fd17b4': {'total_students': 20, 'class_rooms': [{'id': '75378b2d-6d10-4b5b-a7a2-4ed78c99a733', 'students_from_this_division': 20}], 'available_teachers': ['cb1e3391-95c5-4168-ac96-a32948f37781']}, '698b2bcf-a5cf-4f49-b66f-6e4996dfb509': {'total_students': 30, 'class_rooms': [{'id': '75378b2d-6d10-4b5b-a7a2-4ed78c99a733', 'students_from_this_division': 10}, {'id': '11c67b74-a98a-418f-b97b-fc4a4fa6201f', 'students_from_this_division': 20}], 'available_teachers': ['bc38d6d7-d33d-4d7c-b60c-91c6b1ec9f4c']}, 'b45515d5-aa53-4b78-a38c-c749de40818c': {'total_students': 20, 'class_rooms': [{'id': '11c67b74-a98a-418f-b97b-fc4a4fa6201f', 'students_from_this_division': 20}], 'available_teachers': ['36797d3f-c34a-4b7c-8f45-80ce7a3f97db']}}, 'lessons_per_week': 2, 'elective_subject_name': 'second language'}, {'grp_id': 'd50e2029-4086-4c32-a971-5be9d7689999', 'subjectDistributionData': {'27528d28-c8ce-4300-9ddd-5edc19c45e78': {'total_students': 20, 'class_rooms': [{'id': '4ee4cc4e-f163-49d1-a986-e871cbf4169f', 'students_from_this_division': 20}], 'available_teachers': ['549b588a-5ca0-4f45-9865-db23dc824ca2', '39b22a3e-933c-4d49-9b18-4ea7dfbc2423']}, '698b2bcf-a5cf-4f49-b66f-6e4996dfb509': {'total_students': 35, 'class_rooms': [{'id': '4ee4cc4e-f163-49d1-a986-e871cbf4169f', 'students_from_this_division': 20}, {'id': '371c4f70-50cb-48f6-8cd0-7b7201e4bb68', 'students_from_this_division': 15}], 'available_teachers': ['bc38d6d7-d33d-4d7c-b60c-91c6b1ec9f4c']}, 'b45515d5-aa53-4b78-a38c-c749de40818c': {'total_students': 25, 'class_rooms': [{'id': '371c4f70-50cb-48f6-8cd0-7b7201e4bb68', 'students_from_this_division': 25}], 'available_teachers': ['36797d3f-c34a-4b7c-8f45-80ce7a3f97db']}}, 'lessons_per_week': 2, 'elective_subject_name': 'Second Language'}]