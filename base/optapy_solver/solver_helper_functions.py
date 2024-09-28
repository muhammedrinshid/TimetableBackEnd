
from ..time_table_models import Timetable, GradeLevel, ClassSection, Course, Tutor, ClassroomAssignment, Timeslot, Lesson
from ..models import ElectiveGroup,Classroom,Grade,Teacher,Subject,Level,ClassSubject,ClassSubjectSubject,Room
from collections import defaultdict
import uuid
from ..optapy_solver.domain import Timeslot,Lesson,ClassSection,GradeLevelManager,TutorManager,LevelLevelManager,CourseManager,ClassroomAssignmentManager,ClassSectionManager,ElectiveGrpManager

def balance_rooms(rooms, avg_per_classroom, max_iterations=100):
    iteration_count = 0
    while iteration_count < max_iterations:
        iteration_count += 1
        rooms = sorted(rooms, key=lambda x: sum(d["students_from_this_division"] for d in x["students"]))
        smallest_room = rooms[0]
        largest_room = rooms[-1]
        smallest_count = sum(d["students_from_this_division"] for d in smallest_room["students"])
        largest_count = sum(d["students_from_this_division"] for d in largest_room["students"])
        
        if largest_count - smallest_count <= 6:
            break
        
        moved = False
        for division in largest_room["students"]:
            if smallest_count + division["students_from_this_division"] <= avg_per_classroom:
                largest_room["students"].remove(division)
                smallest_room["students"].append(division)
                moved = True
                break
        
        if not moved:
            break  # If we can't move any division, we're done
    
    return rooms

def find_suitable_room(students_distribution, remaining_rooms):
    # Sort the students_distribution list by the number of students in descending order
    sorted_students_distribution = sorted(students_distribution, key=lambda x: x['students_from_this_division'], reverse=True)
    
    # Iterate through the sorted list of students distribution
    for distribution in sorted_students_distribution:
        room_id = distribution['id']
        # Check if the current room's id is in the remaining_rooms dictionary
        if room_id in remaining_rooms:
            room_value = remaining_rooms[room_id]  # Get the corresponding value
            del remaining_rooms[room_id]  # Remove the room from remaining_rooms
            return room_value
    
    # If no suitable room is found, return None
    return None










def get_all_elective_group_of_user(user):
    
    elective_groups = ElectiveGroup.objects.filter(school=user)
    second_selection_groups = [
        group for group in elective_groups 
        if group.be_included_in_second_selection
    ]
    result = []

    for group in elective_groups:
        if not group.be_included_in_second_selection:
            continue
        subject_distribution = defaultdict(lambda: {
            "total_students": 0,
            "class_rooms": [],
            "available_teachers": set(),
            
           
        })

        for class_subject in group.class_subjects.all():
            for class_subject_subject in class_subject.class_subject_subjects.all():
                subject_id = str(class_subject_subject.subject.id)
                subject_data = subject_distribution[subject_id]

                # Update total students
                subject_data["total_students"] += class_subject_subject.number_of_students

                # Add classroom data
                subject_data["class_rooms"].append({
                    "id": str(class_subject.class_room.id),
                    "students_from_this_division": class_subject_subject.number_of_students
                })

                # Add available teachers
                subject_data["available_teachers"].update(
                    str(teacher.id) for teacher in class_subject_subject.assigned_teachers.all()
                )

        # Convert defaultdict to regular dict and set to list
        for subject_id, data in subject_distribution.items():
            data["available_teachers"] = list(data["available_teachers"])
        first_class_subject = group.class_subjects.first()
        elective_subject_name=""
        lessons_per_week=0
        multi_block_lessons=1
        if first_class_subject:
            elective_subject_name = first_class_subject.name
            lessons_per_week = first_class_subject.lessons_per_week
            multi_block_lessons=first_class_subject.multi_block_lessons
        result.append({
            "grp_id": str(group.id),
            "subjectDistributionData": dict(subject_distribution),
            "lessons_per_week":lessons_per_week,
            'multi_block_lessons':multi_block_lessons,
            "elective_subject_name":elective_subject_name,
            "prefered_rooms_for_overflow":group.preferred_rooms.all()
        })
    return(result)












def create_elective_lesson_data(input_data):
    result = []
    
    for group in input_data:
        grp_id = group['grp_id']
        elective_subject_name = group['elective_subject_name']
        lessons_per_week = group['lessons_per_week']
        multi_block_lessons = group['multi_block_lessons']
        prefered_rooms_for_overflow = group['prefered_rooms_for_overflow'].values_list('id', flat=True)

        # Extract unique classroom IDs
        unique_classroom_ids = set()

        for subject_id, subject_data in group['subjectDistributionData'].items():
            for classroom in subject_data['class_rooms']:
                unique_classroom_ids.add(classroom['id'])

        # Convert set back to a list if needed
        unique_classroom_ids_list = list(unique_classroom_ids)
        available_room_stack = {}

        for room_id in unique_classroom_ids_list:
            try:
                # Retrieve the ClassRoom instance by ID
                room_instance = Classroom.objects.get(id=room_id)
                available_room_stack[room_id]=room_instance.room
            except Classroom.DoesNotExist:
                print(f"ClassRoom with ID {room_id} does not exist.")
        
        for subject_id, subject_data in group['subjectDistributionData'].items():
            # Pass the entire subject_data to distribute_students
            distributed_students = distribute_students(subject_data)
            for room_data in distributed_students:
                suitable_room=find_suitable_room(room_data['students'],available_room_stack)
                available_rooms_ids=[]
                if suitable_room is None:

                    if not prefered_rooms_for_overflow:  # Check if the list is empty or None
                        raise ValueError("No preferred rooms for overflow available or list is empty.")
                    available_rooms_ids = list(prefered_rooms_for_overflow)
   
                else:
                    available_rooms_ids.append(suitable_room.id)
                    
                    
                lesson_data = {
                    'subject_id': subject_id,
                    'available_teachers_ids': subject_data['available_teachers'],
                    'class_section_ids': [student['id'] for student in room_data['students']],
                    'elective': grp_id,
                    'students_distribution': {student['id']: student['students_from_this_division'] 
                                              for student in room_data['students']},
                    'lessons_per_week': lessons_per_week,
                    'elective_subject_name': elective_subject_name,
                    'available_rooms_ids':available_rooms_ids,
                    'multi_block_lessons':multi_block_lessons,
                }
                result.append(lesson_data)
    
    return result
    
def distribute_students(data,avg_per_classroom=40):
    total_students = data["total_students"]
    divisions = data["class_rooms"]
    avg_per_classroom = avg_per_classroom
    
    if total_students <= avg_per_classroom + 6:
        return [{"room": 1, "students": divisions}]
    
    current_room = {"room": 1, "students": []}
    current_count = 0
    rooms = []

    for division in sorted(divisions, key=lambda x: x["students_from_this_division"], reverse=True):
        division_size = division["students_from_this_division"]
        
        if current_count == 0 and division_size > avg_per_classroom:
            # If starting a new room and division exceeds average, put it alone
            rooms.append({"room": len(rooms) + 1, "students": [division]})
        elif current_count + division_size <= avg_per_classroom + 6:
            # Add division to current room if it doesn't exceed average + 6
            current_room["students"].append(division)
            current_count += division_size
        else:
            # Current room is full, start a new room
            rooms.append(current_room)
            current_room = {"room": len(rooms) + 1, "students": [division]}
            current_count = division_size

    # Add the last room if it has students
    if current_room["students"]:
        rooms.append(current_room)
    return rooms
    

def create_elective_lesson_ojbects(data, school):
    lessons = []

    for item in data:
        subject_id = item['subject_id']
        subject_from_db = Subject.objects.get(id=subject_id, school=school)
        subject = CourseManager.get_or_create(id=subject_id, name=subject_from_db.name)
        room=None
       
        available_teachers = []
        for teacher in Teacher.objects.filter(id__in=item['available_teachers_ids'], school=school):
            teacher_obj=TutorManager.get_or_create(id=teacher.id,name=teacher.name,min_lessons_per_week=teacher.min_lessons_per_week,max_lessons_per_week=teacher.max_lessons_per_week)
            available_teachers.append(teacher_obj)
        available_rooms = []
        for room in Room.objects.filter(id__in=item['available_rooms_ids'], school=school):
            roomr_obj=ClassroomAssignmentManager.get_or_create(id=room.id,name=room.name,capacity=room.capacity,room_type=room.room_type,occupied=room.occupied)
            available_rooms.append(roomr_obj)

        class_sections = []
        for section_id in item['class_section_ids']:
            classroom = Classroom.objects.get(id=section_id, school=school)
            grade_obj = GradeLevelManager.get_or_create(id=classroom.grade.id, short_name=classroom.grade.short_name)
            classroom_obj = ClassSectionManager.get_or_create(
                id=classroom.id,
                grade=grade_obj,
                division=classroom.division,
                name=classroom.name
            )
            class_sections.append(classroom_obj)

        elective_group = ElectiveGroup.objects.get(id=item['elective'])
        level_obj = LevelLevelManager.get_or_create(id=elective_group.grade.level.id, short_name=elective_group.grade.level.short_name)

        elective = ElectiveGrpManager.get_or_create(
            id=elective_group.id,
            name=elective_group.name,
            grade=grade_obj
        )
        elective_subject_name = item.get('elective_subject_name', '')
        
        for lesson_no in range(1, item['lessons_per_week'] + 1):
            

            lesson = Lesson(
                id= str(uuid.uuid4()),
                subject=subject,
                available_teachers=available_teachers,
                class_sections=class_sections,
                lesson_no=lesson_no,
                available_rooms=available_rooms,
                elective=elective,
                elective_subject_name=elective_subject_name,
                is_elective=True,
                level_level=level_obj,
                multi_block_lessons=item['multi_block_lessons'],
                students_distribution=item['students_distribution']
            )
            lessons.append(lesson)

    return lessons




def create_core_lesson_ojbects(school):

    lessons = []
    for level in Level.objects.filter(school=school):
        level_obj=LevelLevelManager.get_or_create(id=level.id,short_name=level.short_name)

        for grade in Grade.objects.filter(level=level,school=school):
            grade_obj=GradeLevelManager.get_or_create(id=grade.id,short_name=grade.short_name)
            
            for classroom in Classroom.objects.filter(grade=grade):
                classroom_obj=ClassSectionManager.get_or_create(
                    id=classroom.id,grade=grade_obj,division=classroom.division,name=classroom.name
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
                        available_teachers=[TutorManager.get_or_create(id=teacher.id,name=teacher.name,min_lessons_per_week=teacher.min_lessons_per_week,max_lessons_per_week=teacher.max_lessons_per_week) for teacher in class_subject_subject.assigned_teachers.all()]
                        available_rooms = []
                        for room in class_subject_subject.preferred_rooms.all():
                            roomr_obj=ClassroomAssignmentManager.get_or_create(id=room.id,name=room.name,capacity=room.capacity,room_type=room.room_type,occupied=room.occupied)
                            
                            available_rooms.append(roomr_obj) 
                            
                        if len(available_rooms)==0:
                            available_rooms.append(room_obj)
                        for lesson_no in range(1,class_subject.lessons_per_week+1):
                            lesson = Lesson(
                                id=str(uuid.uuid4()),
                                subject=subject_obj,
                                available_teachers=available_teachers,
                                class_sections=[classroom_obj],
                                available_rooms=available_rooms,
                                lesson_no=lesson_no,
                                elective_subject_name=class_subject.name,
                                multi_block_lessons=class_subject.multi_block_lessons,
                                level_level=level_obj

                            )
                            lessons.append(lesson)
    return lessons












