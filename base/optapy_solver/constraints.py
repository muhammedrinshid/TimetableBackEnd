from .domain import Lesson, ClassroomAssignment, Tutor
from optapy import constraint_provider
from optapy.constraint import Joiners, ConstraintFactory
from optapy.score import HardSoftScore
from optapy.types import Constraint, ConstraintCollectors




def dynamic_constraint_provider(user_settings,user):
    @constraint_provider
    def define_constraints(constraint_factory: ConstraintFactory):
        constraints = []

        # Hard constraints (not changeable)
        constraints.extend([
            room_conflict(constraint_factory),
            teacher_conflict(constraint_factory),
            student_group_conflict(constraint_factory),
            ensure_tutor_daily_working_period(constraint_factory),
        ])

        # Changeable constraints
        if user_settings.elective_group_timeslot:
            constraints.append(elective_group_timeslot_constraint(constraint_factory))
        if user_settings.ensure_teacher_assigned:

            constraints.append(ensure_teacher_assigned(constraint_factory))
        if user_settings.ensure_timeslot_assigned:
            constraints.append(ensure_timeslot_assigned(constraint_factory))
        if user_settings.avoid_first_half_period:
            constraints.append(avoid_first_half_period_allocation(constraint_factory,periods_per_day=user.teaching_slots))
        # if user_settings.consecutive_multi_block_lessons:
        #     constraints.append(consecutive_multi_block_lessons(constraint_factory))

        # Soft constraints
        if user_settings.tutor_free_period_constraint:
            constraints.append(tutor_free_period_constraint(constraint_factory,user=user))
        if user_settings.tutor_lesson_load:
            constraints.append(tutor_lesson_load(constraint_factory))
        if user_settings.daily_lesson_limit:
            constraints.append(daily_lesson_limit(constraint_factory,days_per_week=len(user.working_days)))
        if user_settings.prefer_consistent_teacher_for_subject:
            constraints.append(prefer_consistent_teacher_for_subject(constraint_factory))
        if user_settings.prefer_subject_once_per_day:
            constraints.append(prefer_subject_once_per_day(constraint_factory))
        if user_settings.avoid_teacher_consecutive_periods_overlapping_class:
            constraints.append(avoid_teacher_consecutive_periods_overlapping_class(constraint_factory))
        if user_settings.avoid_continuous_subjects:
            constraints.append(avoid_continuous_subjects(constraint_factory))
        if user_settings.avoid_continuous_teaching:
            constraints.append(avoid_continuous_teaching(constraint_factory))
        if user_settings.avoid_consecutive_elective_lessons:
            constraints.append(avoid_consecutive_elective_lessons(constraint_factory))
        if user_settings.avoid_elective_in_first_period :
            constraints.append(avoid_elective_in_first_period(constraint_factory))
        if user_settings.assign_class_teacher_at_first_period :
            constraints.append(assign_class_teacher_at_first_period(constraint_factory))
        if user_settings.same_teacher_first_period_constraint :
            constraints.append(same_teacher_first_period_constraint(constraint_factory))

        return constraints

    return define_constraints




def ensure_teacher_assigned(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .filter(lambda lesson: lesson.allotted_teacher is None) \
        .penalize("Lesson must have a teacher", HardSoftScore.ONE_HARD)

def ensure_timeslot_assigned(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .filter(lambda lesson: lesson.timeslot is None) \
        .penalize("Lesson must have a timeslot", HardSoftScore.ONE_HARD)

def room_conflict(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.timeslot),
              Joiners.equal(lambda lesson: lesson.allotted_room),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .penalize("Room conflict", HardSoftScore.ONE_HARD)

def teacher_conflict(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.timeslot),
              Joiners.equal(lambda lesson: lesson.allotted_teacher),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .penalize("Teacher conflict", HardSoftScore.ONE_HARD)

def student_group_conflict(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.timeslot),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                (any(section in lesson2.class_sections for section in lesson1.class_sections) and
                 (lesson1.elective is None or lesson2.elective is None or lesson1.elective != lesson2.elective))) \
        .penalize("Student group conflict", HardSoftScore.ofHard(1))

def elective_group_timeslot_constraint(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.elective),
              Joiners.equal(lambda lesson: lesson.lesson_no),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: lesson1.elective is not None) \
        .penalize("Elective group timeslot mismatch", HardSoftScore.ONE_HARD,
                  lambda lesson1, lesson2: 1 if lesson1.timeslot != lesson2.timeslot else 0)
        
def avoid_first_half_period_allocation(constraint_factory: ConstraintFactory, periods_per_day):
    # Calculate the maximum period number for the first half of the day
    first_half_period_limit = periods_per_day // 2
    
    return constraint_factory.for_each(Lesson) \
        .filter(lambda lesson: lesson.prevent_first_half_period and lesson.timeslot.period <= first_half_period_limit) \
        .penalize("Avoid lessons in the first half for specific lessons", HardSoftScore.ofHard(1))

        
        
        
        
        
# def consecutive_multi_block_lessons(constraint_factory: ConstraintFactory):
#     return constraint_factory.for_each(Lesson) \
#         .filter(lambda lesson: lesson.multi_block_lessons > 1) \
#         .join(Lesson,
#               Joiners.equal(lambda lesson: (lesson.subject, lesson.class_sections)),
#               Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
#               Joiners.lessThan(lambda lesson: lesson.timeslot.period)) \
#         .filter(lambda lesson1, lesson2:
#                 lesson2.timeslot.period - lesson1.timeslot.period != 1) \
#         .penalize("Non-consecutive multi-block lessons", HardSoftScore.ONE_HARD)

def daily_lesson_limit(constraint_factory: ConstraintFactory, days_per_week: int = 6) -> Constraint:
    return constraint_factory.for_each(Tutor) \
        .join(Lesson, Joiners.equal(lambda tutor: tutor, lambda lesson: lesson.allotted_teacher)) \
        .group_by(
            lambda tutor, lesson: (tutor, lesson.timeslot.day_of_week),
            ConstraintCollectors.countBi()
        ) \
        .filter(lambda tutor_day, lesson_count: 
                lesson_count > (tutor_day[0].max_lessons_per_week / days_per_week)) \
        .penalize(
            "Daily lesson limit", 
            HardSoftScore.ofSoft(2000),  # Lower score
            lambda tutor_day, lesson_count: 
                lesson_count - (tutor_day[0].max_lessons_per_week / days_per_week)
        )


def tutor_lesson_load(constraint_factory: ConstraintFactory) -> Constraint:
    return constraint_factory.for_each(Tutor) \
        .join(Lesson, Joiners.equal(lambda tutor: tutor, lambda lesson: lesson.get_allotted_teacher())) \
        .group_by(lambda tutor, lesson: tutor, ConstraintCollectors.countBi()) \
        .filter(lambda tutor, lesson_count: lesson_count < tutor.min_lessons_per_week or lesson_count > tutor.max_lessons_per_week) \
        .penalize("Tutor lesson load", HardSoftScore.ofSoft(700),
                  lambda tutor, lesson_count: abs(lesson_count - tutor.min_lessons_per_week) 
                  if lesson_count < tutor.min_lessons_per_week 
                  else lesson_count - tutor.max_lessons_per_week)

def prefer_consistent_teacher_for_subject(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                lesson1.allotted_teacher != lesson2.allotted_teacher) \
        .penalize("Prefer consistent teacher for subject and class", HardSoftScore.ofSoft(600))

def prefer_subject_once_per_day(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                any(section in lesson2.class_sections for section in lesson1.class_sections)) \
        .penalize("Prefer subject only once per day per class", HardSoftScore.ofSoft(300))


def avoid_consecutive_elective_lessons(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                lesson1.is_elective and lesson2.is_elective and
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid consecutive elective lessons", HardSoftScore.ofSoft(200))
        
        
def avoid_teacher_consecutive_periods_overlapping_class(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.allotted_teacher),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                lesson2.timeslot.period - lesson1.timeslot.period == 1 and lesson1.multi_block_lessons==1 and lesson2.multi_block_lessons==1 and 
                any(section in lesson2.class_sections for section in lesson1.class_sections)) \
        .penalize("Avoid teacher consecutive periods with overlapping classes", HardSoftScore.ofSoft(100))
        
             
def avoid_continuous_subjects(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid continuous subjects", HardSoftScore.ofSoft(300))

def avoid_continuous_teaching(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.allotted_teacher),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid continuous teaching", HardSoftScore.ofSoft(25))

   
def tutor_free_period_constraint(constraint_factory: ConstraintFactory,user):
    periods_per_day=user.teaching_slots
    return constraint_factory.forEach(Tutor) \
        .join(Lesson,
              Joiners.equal(lambda tutor: tutor, lambda lesson: lesson.allotted_teacher)) \
        .groupBy(lambda tutor, lesson: tutor,
                 ConstraintCollectors.countDistinct(lambda tutor, lesson: (lesson.timeslot.day_of_week, lesson.timeslot.period))) \
        .filter(lambda tutor, lesson_count: lesson_count == periods_per_day) \
        .penalize("Tutor should have at least one free period per day", HardSoftScore.ofSoft(700))

def ensure_tutor_daily_working_period(constraint_factory: ConstraintFactory):
    return constraint_factory.forEach(Tutor) \
        .join(Lesson,
              Joiners.equal(lambda tutor: tutor, lambda lesson: lesson.allotted_teacher)) \
        .groupBy(lambda tutor, lesson: (tutor, lesson.timeslot.day_of_week),
                 ConstraintCollectors.countBi()) \
        .filter(lambda tutor_day, lesson_count: lesson_count == 0) \
        .penalize("Tutor should have at least one working period per day", HardSoftScore.ofSoft(500))
        
        
        
def avoid_elective_in_first_period(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .filter(lambda lesson: lesson.is_elective and lesson.timeslot.period == 1) \
        .penalize("Avoid elective lessons in the first period", HardSoftScore.ofSoft(100))

def assign_class_teacher_at_first_period(constraint_factory) -> Constraint:
    """
    Prioritizes assigning class teachers to their class sections in the first period for core subjects.
    Penalizes when the class teacher is not teaching their class in first period.
    """
    return constraint_factory.for_each(Lesson)\
        .filter(lambda lesson: 
            # Filter for core subjects (not electives)
            not lesson.is_elective
            # Check if there's only one class section
            and len(lesson.class_sections) == 1
            # Check if it's first period
            and lesson.timeslot is not None 
            and lesson.timeslot.period == 1
            # Check if the class has a class teacher
            and lesson.class_sections[0].class_teacher is not None
            # Check if allotted teacher is different from class teacher
            and lesson.allotted_teacher != lesson.class_sections[0].class_teacher)\
        .penalize("Class teacher not teaching first period", HardSoftScore.ofSoft(50))
        
def same_teacher_first_period_constraint(constraint_factory) -> Constraint:
    """
    Encourages assigning the same teacher for first period core subjects 
    for a class section across different days.
    Penalizes when different teachers are assigned to first period.
    """
    return constraint_factory.for_each(Lesson)\
        .join(Lesson,
              # Same class sections
              Joiners.equal(lambda lesson: lesson.class_sections),
              # Different lessons
              Joiners.less_than(lambda lesson: lesson.id))\
        .filter(lambda lesson1, lesson2:
            lesson1.timeslot is not None 
            and lesson2.timeslot is not None
            and lesson1.timeslot.period == 1
            and lesson2.timeslot.period == 1
            and lesson1.timeslot.day_of_week != lesson2.timeslot.day_of_week
            and not lesson1.is_elective 
            and not lesson2.is_elective
            and len(lesson1.class_sections) == 1
            and len(lesson2.class_sections) == 1
            and lesson1.allotted_teacher is not None
            and lesson2.allotted_teacher is not None
            and lesson1.allotted_teacher != lesson2.allotted_teacher)\
        .penalize("Different teachers for first period", HardSoftScore.ofSoft(50))