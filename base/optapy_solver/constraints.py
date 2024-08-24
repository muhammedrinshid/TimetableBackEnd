from .domain import Lesson, ClassroomAssignment
from optapy import constraint_provider
from optapy.constraint import Joiners, ConstraintFactory
from optapy.score import HardSoftScore

@constraint_provider
def define_constraints(constraint_factory: ConstraintFactory):
    return [
        # Hard constraints
        room_conflict(constraint_factory),
        teacher_conflict(constraint_factory),
        student_group_conflict(constraint_factory),
        elective_group_timeslot_constraint(constraint_factory),

        # Soft constraints are only implemented in the optapy-quickstarts code
        
        
        avoid_continuous_subjects(constraint_factory),
        avoid_continuous_teaching(constraint_factory),
        avoid_consecutive_elective_lessons(constraint_factory),
        prefer_subject_once_per_day(constraint_factory),
        avoid_teacher_consecutive_periods_overlapping_class(constraint_factory),
        prefer_consistent_teacher_for_subject(constraint_factory),
    ]

def room_conflict(constraint_factory: ConstraintFactory):
    # A room can accommodate at most one lesson at the same time.
    return constraint_factory.for_each(Lesson) \
            .join(Lesson,
                  # ... in the same timeslot ...
                  Joiners.equal(lambda lesson: lesson.timeslot),
                  # ... in the same room ...
                  Joiners.equal(lambda lesson: lesson.alotted_room),
                  # ... and the pair is unique (different id, no reverse pairs) ...
                  Joiners.less_than(lambda lesson: lesson.id)
             ) \
            .penalize("Room conflict", HardSoftScore.ONE_HARD)


def teacher_conflict(constraint_factory: ConstraintFactory):
    # A teacher can teach at most one lesson at the same time.
    return constraint_factory.for_each(Lesson) \
                .join(Lesson,
                      Joiners.equal(lambda lesson: lesson.timeslot),
                      Joiners.equal(lambda lesson: lesson.alotted_teacher),
                      Joiners.less_than(lambda lesson: lesson.id)
                ) \
                .penalize("Teacher conflict", HardSoftScore.ONE_HARD)


def student_group_conflict(constraint_factory: ConstraintFactory):
    # A student can attend at most one lesson at the same time, with an exception for electives
    return constraint_factory.for_each(Lesson) \
            .join(Lesson,
                  Joiners.equal(lambda lesson: lesson.timeslot),
                  Joiners.less_than(lambda lesson: lesson.id)
            ) \
            .filter(lambda lesson1, lesson2: 
                    (any(section in lesson2.class_sections for section in lesson1.class_sections) and
                     (lesson1.elective is None or lesson2.elective is None or lesson1.elective != lesson2.elective))
            ) \
            .penalize("Student group conflict", HardSoftScore.ONE_HARD)



def elective_group_timeslot_constraint(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.elective),
              Joiners.equal(lambda lesson: lesson.lesson_no),
              Joiners.less_than(lambda lesson: lesson.id)
        ) \
        .filter(lambda lesson1, lesson2: lesson1.elective is not None) \
        .penalize("Elective group timeslot mismatch", HardSoftScore.ONE_HARD,
                  lambda lesson1, lesson2: 
                      1 if lesson1.timeslot != lesson2.timeslot else 0)
        
        






def avoid_continuous_subjects(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week)
        ) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid continuous subjects", HardSoftScore.ONE_SOFT)

def avoid_continuous_teaching(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.alotted_teacher),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week)
        ) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid continuous teaching", HardSoftScore.ONE_SOFT)
        
        
def avoid_consecutive_elective_lessons(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.class_sections),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week)
        ) \
        .filter(lambda lesson1, lesson2: 
                lesson1.is_elective and lesson2.is_elective and
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1) \
        .penalize("Avoid consecutive elective lessons", HardSoftScore.ONE_SOFT)
        
        
def avoid_teacher_consecutive_periods_overlapping_class(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.alotted_teacher),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week)
        ) \
        .filter(lambda lesson1, lesson2: 
                abs(lesson1.timeslot.period - lesson2.timeslot.period) == 1 and
                any(section in lesson2.class_sections for section in lesson1.class_sections)) \
        .penalize("Avoid teacher consecutive periods with overlapping classes", HardSoftScore.ONE_SOFT)
        
        
        
        
def prefer_subject_once_per_day(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: lesson.timeslot.day_of_week)
        ) \
        .filter(lambda lesson1, lesson2: 
                lesson1.id < lesson2.id and
                any(section in lesson2.class_sections for section in lesson1.class_sections)) \
        .penalize("Prefer subject only once per day per class", HardSoftScore.ONE_SOFT)
        
def prefer_consistent_teacher_for_subject(constraint_factory: ConstraintFactory):
    return constraint_factory.for_each(Lesson) \
        .join(Lesson,
              Joiners.equal(lambda lesson: lesson.subject),
              Joiners.equal(lambda lesson: tuple(lesson.class_sections))
        ) \
        .filter(lambda lesson1, lesson2: 
                lesson1.id < lesson2.id and
                lesson1.alotted_teacher != lesson2.alotted_teacher) \
        .penalize("Prefer consistent teacher for subject and class", HardSoftScore.ONE_SOFT)