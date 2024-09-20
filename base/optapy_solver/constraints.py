from .domain import Lesson, ClassroomAssignment, Tutor
from optapy import constraint_provider
from optapy.constraint import Joiners, ConstraintFactory
from optapy.score import HardSoftScore
from optapy.types import Constraint, ConstraintCollectors




def dynamic_constraint_provider(user_settings):
    @constraint_provider
    def define_constraints(constraint_factory: ConstraintFactory):
        constraints = []

        # Hard constraints (not changeable)
        constraints.extend([
            room_conflict(constraint_factory),
            teacher_conflict(constraint_factory),
            student_group_conflict(constraint_factory),
        ])

        # Changeable constraints
        if user_settings.elective_group_timeslot:
            constraints.append(elective_group_timeslot_constraint(constraint_factory))
        if user_settings.ensure_teacher_assigned:

            constraints.append(ensure_teacher_assigned(constraint_factory))
        if user_settings.ensure_timeslot_assigned:
            constraints.append(ensure_timeslot_assigned(constraint_factory))

        # Soft constraints
        if user_settings.tutor_lesson_load:
            constraints.append(tutor_lesson_load(constraint_factory))
        if user_settings.daily_lesson_limit:
            constraints.append(daily_lesson_limit(constraint_factory))
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

        return constraints

    return define_constraints





# @constraint_provider
# def define_constraints(constraint_factory: ConstraintFactory):
#     return [
#         # Hard constraints
#         room_conflict(constraint_factory),
#         teacher_conflict(constraint_factory),
#         student_group_conflict(constraint_factory),
#         elective_group_timeslot_constraint(constraint_factory),
#         ensure_teacher_assigned(constraint_factory),
#         ensure_timeslot_assigned(constraint_factory),
        
#         # Soft constraints (ordered by priority)
#         tutor_lesson_load(constraint_factory),
#         daily_lesson_limit(constraint_factory),
#         prefer_consistent_teacher_for_subject(constraint_factory),
#         prefer_subject_once_per_day(constraint_factory),
#         avoid_teacher_consecutive_periods_overlapping_class(constraint_factory),
#         avoid_continuous_subjects(constraint_factory),
#         avoid_continuous_teaching(constraint_factory),
#         avoid_consecutive_elective_lessons(constraint_factory),
#     ]

# Hard constraints

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
        .penalize("Student group conflict", HardSoftScore.ONE_HARD)

def elective_group_timeslot_constraint(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.elective),
              Joiners.equal(lambda lesson: lesson.lesson_no),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: lesson1.elective is not None) \
        .penalize("Elective group timeslot mismatch", HardSoftScore.ONE_HARD,
                  lambda lesson1, lesson2: 1 if lesson1.timeslot != lesson2.timeslot else 0)

# Soft constraints


def daily_lesson_limit(constraint_factory: ConstraintFactory) -> Constraint:
    return constraint_factory.for_each(Tutor) \
        .join(Lesson, Joiners.equal(lambda tutor: tutor, lambda lesson: lesson.allotted_teacher)) \
        .group_by(
            lambda tutor, lesson: (tutor, lesson.timeslot.day_of_week),
            ConstraintCollectors.countBi()
        ) \
        .filter(lambda tutor_day, lesson_count: lesson_count > tutor_day[0].max_lessons_per_week / 5) \
        .penalize(
            "Daily lesson limit", 
            HardSoftScore.ofSoft(800),
            lambda tutor_day, lesson_count: lesson_count - (tutor_day[0].max_lessons_per_week / 5)
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
        .penalize("Prefer subject only once per day per class", HardSoftScore.ofSoft(400))

def avoid_teacher_consecutive_periods_overlapping_class(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.allotted_teacher),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                lesson2.timeslot.period - lesson1.timeslot.period == 1 and
                any(section in lesson2.class_sections for section in lesson1.class_sections)) \
        .penalize("Avoid teacher consecutive periods with overlapping classes", HardSoftScore.ofSoft(200))

def avoid_continuous_subjects(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid continuous subjects", HardSoftScore.ofSoft(100))

def avoid_continuous_teaching(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.allotted_teacher),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid continuous teaching", HardSoftScore.ofSoft(50))

def avoid_consecutive_elective_lessons(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week),
              Joiners.less_than(lambda lesson: lesson.id)) \
        .filter(lambda lesson1, lesson2: 
                lesson1.is_elective and lesson2.is_elective and
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid consecutive elective lessons", HardSoftScore.ofSoft(25))