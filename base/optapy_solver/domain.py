from optapy import problem_fact, planning_id
from optapy import planning_entity, planning_variable,planning_pin
from optapy import planning_solution, planning_entity_collection_property, \
                   problem_fact_collection_property, \
                   value_range_provider, planning_score
from optapy.score import HardSoftScore
from datetime import time




@problem_fact
class ClassroomAssignment:
    def __init__(self, id, name,capacity,room_type,occupied):
        self.id = id
        self.name = name
        self.capacity=capacity
        self.room_type=room_type
        self.occupied=occupied
        

    @planning_id
    def get_id(self):
        return self.id

    def __str__(self):
        return f"Room( name={self.name})"
    
class ClassroomAssignmentManager:
    _registry = {}

    @classmethod
    def get_or_create(cls,id, name,capacity,room_type,occupied):
        if id in cls._registry:
            return cls._registry[id]
        else:
            new_instance = ClassroomAssignment(id, name,capacity,room_type,occupied)
            cls._registry[id] = new_instance
            return new_instance
        
        
        
        
        
        
        
        

@problem_fact
class Timeslot:
    def __init__(self, id, day_of_week,period):
        self.id = id
        self.day_of_week = day_of_week
        self.period=period

    @planning_id
    def get_id(self):
        return self.id

    def __str__(self):
        return (
        f"Timeslot("
        f"period={self.period}, "
        f"day_of_week={self.day_of_week})"
    )




@problem_fact
class ElectiveGrp:
    def __init__(self, id, name,standard):
        self.id = id
        self.name = name
        self.standard=standard

    @planning_id
    def get_id(self):
        return self.id

    def __str__(self):
        return (
        f"ElectiveGrp("
        
        f"name={self.name})"
    )

class ElectiveGrpManager:
    _registry = {}

    @classmethod
    def get_or_create(cls, id, name,standard):
        if id in cls._registry:
            return cls._registry[id]
        else:
            new_instance = ElectiveGrp(id, name,standard)
            cls._registry[id] = new_instance
            return new_instance
        
        
        
        
        
    
@problem_fact
class StandardLevel:
    def __init__(self,id,short_name) :
        self.id = id
        self.short_name = short_name
    @planning_id
    def get_id(self):
        return self.id

    def __str__(self):
        return f" standard ={self.short_name}"
    

class StandardLevelManager:
    _registry = {}

    @classmethod
    def get_or_create(cls, id,short_name):
        if id in cls._registry:
            return cls._registry[id]
        else:
            new_instance = StandardLevel(id,short_name)
            cls._registry[id] = new_instance
            return new_instance







# Classroom
@problem_fact
class ClassSection():
    def __init__(self,id,standard,division,name):
        self.id=id
        self.standard=standard
        self.division=division
        self.name=name
    @planning_id
    def get_id(self):
        return self.id
    def __str__(self):
         return f"Classroom {self.standard.short_name} - {self.division}"


class ClassSectionManager:
    _registry = {}

    @classmethod
    def get_or_create(cls, id, standard,division,name):
        if id in cls._registry:
            return cls._registry[id]
        else:
            new_instance = ClassSection(id,standard,division,name)
            cls._registry[id] = new_instance
            return new_instance


        
        
        
        
        
# Subject
@problem_fact
class Course:
    def __init__(self,id,name):
        self.id = id
        self.name = name

    @planning_id
    def get_id(self):
        return self.id

    def __str__(self):
        return f"subject (name={self.name})"
    
    
class CourseManager:
    _registry = {}

    @classmethod
    def get_or_create(cls, id, name):
        if id in cls._registry:
            return cls._registry[id]
        else:
            new_instance = Course(id, name)
            cls._registry[id] = new_instance
            return new_instance








@problem_fact
class Tutor:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    @planning_id
    def get_id(self):
        return self.id

    def __str__(self):
        return f"Teacher( name={self.name})"
    
class TutorManager:
    _registry = {}

    @classmethod
    def get_or_create(cls, id, name):
        if id in cls._registry:
            return cls._registry[id]
        else:
            new_instance = Tutor(id, name)
            cls._registry[id] = new_instance
            return new_instance

    
    
    
    
    
    
    
    
    
    
    
@planning_entity
class Lesson:
    def __init__(self, id, subject, available_teachers, class_sections, lesson_no,available_rooms, is_elective=False,alotted_room=None, timeslot=None, alotted_teacher=None, elective=None, students_distribution=None, elective_subject_name=''):
        self.id = id
        self.subject = subject
        self.alotted_teacher = alotted_teacher
        self.available_teachers = available_teachers
        self.alotted_room=alotted_room
        self.class_sections = class_sections
        self.timeslot = timeslot
        self.available_rooms = available_rooms
        self.elective = elective
        self.students_distribution = students_distribution
        self.lesson_no = lesson_no
        self.elective_subject_name = elective_subject_name
        self.is_elective = is_elective
        

    @planning_id
    def get_id(self):
        return self.id

    @planning_variable(Timeslot, value_range_provider_refs=["timeslotRange"])
    def get_timeslot(self):
        return self.timeslot

    def set_timeslot(self, new_timeslot):
        self.timeslot = new_timeslot

    @planning_variable(ClassroomAssignment, value_range_provider_refs=["roomRange"])
    def get_alotted_room(self):
        return self.alotted_room

    def set_alotted_room(self, new_room):
        self.alotted_room = new_room

   
    
    @planning_variable(Tutor, value_range_provider_refs=['teacherRange'])
    def get_alotted_teacher(self):
        return self.alotted_teacher

    def set_alotted_teacher(self, teacher):
        self.alotted_teacher = teacher

    @problem_fact_collection_property(Tutor)
    @value_range_provider('teacherRange')
    def get_teacher_range(self):
        return self.available_teachers
    
    
    
    @problem_fact_collection_property(ClassroomAssignment)
    @value_range_provider('roomRange')
    def get_room_range(self):
        return self.available_rooms

    def __str__(self):
        return (
            f"Lesson("
            f"timeslot={self.timeslot}, "
            f"room={self.alotted_room}, "
            f"teacher={self.alotted_teacher}, "
            f"subject={self.subject}, "
            f"number={self.lesson_no}, "
            f")"
        )



def format_list(a_list):
    return ',\n'.join(map(str, a_list))

@planning_solution
class TimeTable:
    def __init__(self, timeslot_list, lesson_list ,score=None):
        self.timeslot_list = timeslot_list
        self.lesson_list = lesson_list
        self.score = score
        
        
        
        
    @problem_fact_collection_property(Timeslot)
    @value_range_provider("timeslotRange")
    def get_timeslot_list(self):
        return self.timeslot_list

    
   





    @planning_entity_collection_property(Lesson)
    def get_lesson_list(self):
        return self.lesson_list

    @planning_score(HardSoftScore)
    def get_score(self):
        return self.score

    def set_score(self, score):
        self.score = score

    def __str__(self):
        return (
            f"TimeTable("
            f"timeslot_list={format_list(self.timeslot_list)},\n"
            f"lesson_list={format_list(self.lesson_list)},\n"
            f"score={str(self.score.toString()) if self.score is not None else 'None'}"
            f")"
        )