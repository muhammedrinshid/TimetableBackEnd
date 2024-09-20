from .domain import TimeTable
from .domain import Timeslot,Lesson,ClassSection,StandardLevelManager,TutorManager,CourseManager,ClassroomAssignmentManager,ClassSectionManager
import uuid
from optapy.constraint import ConstraintMatchTotal
from base.models import UserConstraintSettings


from .solver_helper_functions import create_core_lesson_ojbects,create_elective_lesson_ojbects,get_all_elective_group_of_user,create_elective_lesson_data
import optapy.config
from optapy.types import Duration
from optapy import solver_factory_create
from .constraints import dynamic_constraint_provider
from optapy import config, solver_factory_create



def print_timetable(solution):
    for lesson in solution.get_lesson_list():
        print(f"Lesson: {lesson.subject}, Teacher: {lesson.allotted_teacher.name}, "
              f"Room: {lesson.get_allotted_room().name if lesson.get_allotted_room() else 'Not assigned'}, "
              f"Timeslot: {lesson.get_timeslot().day_of_week} - Period {lesson.get_timeslot().period}"
              f"Timeslot: {lesson.class_sections}"
              )

def run_optimization(request):
    problem = create_problem_from_django_models(request.user)
    
    # Create a solver config
    solver_config = config.solver.SolverConfig()
    
    # Set the model
    solver_config.withEntityClasses(Lesson)
    solver_config.withSolutionClass(TimeTable)
    
    
    user_settings = UserConstraintSettings.objects.get(user=request.user)

    constraint_provider = dynamic_constraint_provider(user_settings)

    # Set the constraint provider
    solver_config.withConstraintProviderClass(constraint_provider)
    
    # Set termination condition
    solver_config.withTerminationSpentLimit(Duration.ofSeconds(15))
    
    # Configure phases
    construction_heuristic_phase = config.constructionheuristic.ConstructionHeuristicPhaseConfig()
    local_search_phase = config.localsearch.LocalSearchPhaseConfig()
    
    # Configure local search
    local_search_phase.setLocalSearchType(config.localsearch.LocalSearchType.LATE_ACCEPTANCE)
    
    # Set phases using OptaPy's native method
    solver_config.withPhases(construction_heuristic_phase, local_search_phase)
    
    # Create solver and solve
    solver = solver_factory_create(solver_config).buildSolver()
    solution = solver.solve(problem)
    
    # Directly access the score attribute from the solution
    score = solution.score
    
    # Add logging or debugging output
    print(f"Best score: {score}")
    print(f"Number of lessons scheduled: {len(solution.lesson_list)}, Total Number of Lessons to Schedule: {len(problem.lesson_list)}")
    
    # Violated constraints are usually identified by setting up Constraint Match Totals, this will depend on how constraints are tracked
    # This will require setting up constraint matches when you define your constraints
    
    return solution

def create_problem_from_django_models(user):
    from ..models import User, Room, Grade, Standard, Classroom, ClassSubject, ClassSubjectSubject, Teacher
    school = user 
    rooms = [ClassroomAssignmentManager.get_or_create(id=room.id,name= room.name,capacity=room.capacity,room_type=room.room_type,occupied=room.occupied) for room in Room.objects.filter(school=school)]
    tutors=[TutorManager.get_or_create(id=teacher.id,name=teacher.name,min_lessons_per_week=teacher.min_lessons_per_week,max_lessons_per_week=teacher.max_lessons_per_week) for teacher in Teacher.objects.filter(school=school)]
    for teacher in tutors:
        print(teacher.name,teacher.min_lessons_per_week,teacher.max_lessons_per_week)
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
    # debug=timeslots
    # for item in debug:
        
    #     print(type(item))
    # attributes = vars(debug)
    # for attr_name, attr_value in attributes.items():
    #    print(f"Name: {attr_name}, Value: {attr_value}, Type: {type(attr_value).__name__}")
    return TimeTable(timeslot_list=timeslots, lesson_list=lessons ,tutors=tutors)

















