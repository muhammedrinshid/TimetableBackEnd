from rest_framework import serializers
from ...time_table_models import Timetable
from rest_framework import serializers
from ...models import  Teacher, Room, Subject, Classroom
from ...time_table_models import Timetable,  Lesson,LessonClassSection,Tutor,ClassSection
from .user_serializer import SubjectSerializer
from uuid import uuid4
class TimetableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timetable
        # Specify the fields to include, excluding 'school' and 'updated'
        fields = [
            'id',
            'name',
            'score',
            'soft_score',
            'hard_score',
            'optimal',
            'feasible',
            'created',
            'is_default'
        ]
        
        
        
class TimetableUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timetable
        fields = ['name']
        
# serializers.py


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['name', 'room_number', 'room_type','id']

class ClassDetailsSerializer(serializers.ModelSerializer):
    standard = serializers.CharField(source='class_section.classroom.standard.short_name')
    division = serializers.CharField(source='class_section.classroom.division')
    id=serializers.UUIDField(source='class_section.classroom.id')
    number_of_students = serializers.IntegerField()

    class Meta:
        model = LessonClassSection
        fields = ['id','standard', 'division', 'number_of_students']
class TeacherSessionSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='course.name')
    subject_id = serializers.UUIDField(source='course.subject.id')
    type = serializers.SerializerMethodField()
    elective_subject_name = serializers.CharField()
    room = RoomSerializer(source='classroom_assignment.room')
    class_details = ClassDetailsSerializer(source='lessonclasssection_set', many=True)
    session_key=serializers.SerializerMethodField()
    class Meta:
        model = Lesson
        fields = ['subject','subject_id', 'type', 'elective_subject_name', 'room', 'class_details','elective_group_id','session_key']

    def get_type(self, obj):
        return 'Elective' if obj.is_elective else 'Core'

    def to_representation(self, instance):
        if instance is None:
            # Return a dictionary with all fields set to None
            return {field: None for field in self.Meta.fields}
        return super().to_representation(instance)
    def get_session_key(self, obj):
        return str(uuid4())  # Generate a new UUID for each instance

class InstructorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='teacher.name')
    profile_image = serializers.CharField(source='teacher.profile_image.url')
    surname = serializers.CharField(source='teacher.surname')
    teacher_id = serializers.CharField(source='teacher.teacher_id')
    id = serializers.CharField(source='teacher.id')
    qualified_subjects=SubjectSerializer(source='teacher.qualified_subjects', many=True, read_only=True,)
    class Meta:
        model = Tutor
        fields = ['id','name', 'profile_image', 'surname', 'teacher_id','qualified_subjects']

class TeacherDayTimetableSerializer(serializers.Serializer):
    instructor = InstructorSerializer()
    sessions = serializers.ListField(child=TeacherSessionSerializer(many=True))


class WholeTeacherWeekTimetableSerializer(serializers.Serializer):
    MON = TeacherDayTimetableSerializer(many=True, required=False)
    TUE = TeacherDayTimetableSerializer(many=True, required=False)
    WED = TeacherDayTimetableSerializer(many=True, required=False)
    THU = TeacherDayTimetableSerializer(many=True, required=False)
    FRI = TeacherDayTimetableSerializer(many=True, required=False)
    SAT = TeacherDayTimetableSerializer(many=True, required=False)
    SUN = TeacherDayTimetableSerializer(many=True, required=False)

    def __init__(self, *args, **kwargs):
        working_days = kwargs.pop('working_days', [])
        super().__init__(*args, **kwargs)

        for day in ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
            if day not in working_days:
                self.fields.pop(day)













class ClassroomSerializer(serializers.ModelSerializer):
    standard = serializers.CharField(source='standard.short_name')
    room = RoomSerializer()

    class Meta:
        model = Classroom
        fields = ['standard', 'room']

class ClassSectionSerializer(serializers.ModelSerializer):
    standard = serializers.CharField(source='classroom.standard.short_name')
    room = RoomSerializer(source='classroom.room')
    total_students = serializers.CharField(source='classroom.number_of_students')
    class_id=serializers.CharField(source='classroom.class_id')
    id=serializers.UUIDField(source='classroom.id')
    class Meta:
        model = ClassSection
        fields = ['id','standard', 'division', 'room', 'total_students','class_id']

   
class ClassDistributionSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='lesson.course.name')
    teacher = serializers.SerializerMethodField()
    number_of_students_from_this_class = serializers.IntegerField(source='number_of_students')
    room = serializers.SerializerMethodField()

    class Meta:
        model = LessonClassSection
        fields = ['subject', 'teacher', 'number_of_students_from_this_class', 'room']

    def get_teacher(self, obj):
        teacher = obj.lesson.allotted_teacher.teacher
        return {
            'name': f"{teacher.name} {teacher.surname}".strip(),
            'profile_image': teacher.profile_image.url if teacher.profile_image else None,
        }

    def get_room(self, obj):
        room = obj.lesson.classroom_assignment.room
        return {
            'name': room.name,
            'number': room.room_number,
            'type': room.get_room_type_display(),
        }

class StudentSessionSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    elective_id = serializers.SerializerMethodField()  # Use SerializerMethodField here
    class_distribution = serializers.SerializerMethodField()

    def get_name(self, obj):
        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return None
        return ', '.join(set(lesson.elective_subject_name if lesson.is_elective else lesson.course.name for lesson in obj))

    def get_type(self, obj):
        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return None
        types = set('Elective' if lesson.is_elective else 'Core' for lesson in obj)
        return ', '.join(types)
    def get_elective_id(self, obj):
        print("hi")

        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return None
        
        first_lesson = obj[0]
        
        # Return the elective_group_id if it's an elective lesson, else None
        return first_lesson.elective_group_id if first_lesson.is_elective and first_lesson.elective_group_id else None

    def get_class_distribution(self, obj):
        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return []
        
        distribution = []
        for lesson in obj:
            current_class_section = self.context.get('class_section')
            
            try:
                lcs = LessonClassSection.objects.get(lesson=lesson, class_section=current_class_section)
                distribution.append({
                    'subject': lesson.course.name,
                    'teacher': {
                        'name': f"{lesson.allotted_teacher.teacher.name} {lesson.allotted_teacher.teacher.surname}".strip(),
                        'profile_image': lesson.allotted_teacher.teacher.profile_image.url if lesson.allotted_teacher.teacher.profile_image else None,
                        'id': lesson.allotted_teacher.teacher.id,
                    },
                    'number_of_students_from_this_class': lcs.number_of_students,
                    'room': {
                        'name': lesson.classroom_assignment.room.name,
                        'number': lesson.classroom_assignment.room.room_number,
                        'type': lesson.classroom_assignment.room.get_room_type_display(),
                    }
                })
            except LessonClassSection.DoesNotExist:
                pass

        return distribution
    
    
class StudentDayTimetableSerializer(serializers.Serializer):
    classroom = ClassSectionSerializer()
    sessions = serializers.SerializerMethodField()

    def get_sessions(self, obj):
        # Handle the nested structure: sessions[period][group]
        formatted_sessions = []
        for period_groups in obj['sessions']:
            if not period_groups:  # Empty period
                formatted_sessions.append([])
                continue
                
            period_data = []
            for lesson_group in period_groups:
                if lesson_group:  # Skip empty groups
                    period_data.append(
                        StudentSessionSerializer(
                            lesson_group, 
                            context={'class_section': obj['classroom']}
                        ).data
                    )
            formatted_sessions.append(period_data)
            
        return formatted_sessions
    
    
class StudentWeekTimetableSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        working_days = kwargs.pop('working_days', [])
        super().__init__(*args, **kwargs)

        for day in working_days:
            self.fields[day] = StudentDayTimetableSerializer(many=True)




class ClassroomWeekTimetableSerializer(serializers.Serializer):
    day = serializers.CharField()
    sessions = StudentSessionSerializer(many=True)

    def get_sessions(self, obj):
        return StudentSessionSerializer(obj['sessions'], many=True, context={'class_section': self.context['class_section']}).data

class TeacherWeekTimetableSerializer(serializers.Serializer):
    day = serializers.CharField()
    sessions = TeacherSessionSerializer(many=True)

    







