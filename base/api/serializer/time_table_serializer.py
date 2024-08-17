from rest_framework import serializers
from ...time_table_models import Timetable
from rest_framework import serializers
from ...models import  Teacher, Room, Subject, Classroom
from ...time_table_models import Timetable,  Lesson,LessonClassSection,Tutor,ClassSection
class TimetableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timetable
        # Specify the fields to include, excluding 'school' and 'updated'
        fields = [
            'id',
            'name',
            'score',
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
        fields = ['name', 'room_number', 'room_type']

class ClassDetailsSerializer(serializers.ModelSerializer):
    standard = serializers.CharField(source='class_section.classroom.standard.short_name')
    division = serializers.CharField(source='class_section.classroom.division')
    number_of_students = serializers.IntegerField()

    class Meta:
        model = LessonClassSection
        fields = ['standard', 'division', 'number_of_students']
class SessionSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='course.name')
    type = serializers.SerializerMethodField()
    elective_subject_name = serializers.CharField()
    room = RoomSerializer(source='classroom_assignment.room')
    class_details = ClassDetailsSerializer(source='lessonclasssection_set', many=True)

    class Meta:
        model = Lesson
        fields = ['subject', 'type', 'elective_subject_name', 'room', 'class_details']

    def get_type(self, obj):
        return 'Elective' if obj.is_elective else 'Core'

    def to_representation(self, instance):
        if instance is None:
            # Return a dictionary with all fields set to None
            return {field: None for field in self.Meta.fields}
        return super().to_representation(instance)

class InstructorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='teacher.name')
    profile_image = serializers.CharField(source='teacher.profile_image')
    surname = serializers.CharField(source='teacher.surname')
    teacher_id = serializers.CharField(source='teacher.teacher_id')

    class Meta:
        model = Tutor
        fields = ['name', 'profile_image', 'surname', 'teacher_id']

class TeacherDayTimetableSerializer(serializers.Serializer):
    instructor = InstructorSerializer()
    sessions = SessionSerializer(many=True)


class TeacherWeekTimetableSerializer(serializers.Serializer):
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
    total_students = serializers.SerializerMethodField()

    class Meta:
        model = ClassSection
        fields = ['standard', 'division', 'room', 'total_students']

    def get_total_students(self, obj):
        return sum(lcs.number_of_students for lcs in obj.lessonclasssection_set.all())
class ClassDistributionSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='lesson.course.name')
    teacher = serializers.SerializerMethodField()
    number_of_students_from_this_class = serializers.IntegerField(source='number_of_students')
    room = serializers.SerializerMethodField()

    class Meta:
        model = LessonClassSection
        fields = ['subject', 'teacher', 'number_of_students_from_this_class', 'room']

    def get_teacher(self, obj):
        teacher = obj.lesson.alotted_teacher.teacher
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
class SessionSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    class_distribution = serializers.SerializerMethodField()

    def get_name(self, obj):
        if not obj:
            return None
        return ', '.join(set(lesson.elective_subject_name if lesson.is_elective else lesson.course.name for lesson in obj))

    def get_type(self, obj):
        if not obj:
            return None
        types = set('Elective' if lesson.is_elective else 'Core' for lesson in obj)
        return ', '.join(types)

    def get_class_distribution(self, obj):
        if not obj:
            return []
        
        distribution = []
        for lesson in obj:
            for lcs in lesson.lessonclasssection_set.all():
                distribution.append({
                    'subject': lesson.course.name,
                    'teacher': {
                        'name': f"{lesson.alotted_teacher.teacher.name} {lesson.alotted_teacher.teacher.surname}".strip(),
                        'profile_image': lesson.alotted_teacher.teacher.profile_image.url if lesson.alotted_teacher.teacher.profile_image else None,
                    },
                    'number_of_students_from_this_class': lcs.number_of_students,
                    'room': {
                        'name': lesson.classroom_assignment.room.name,
                        'number': lesson.classroom_assignment.room.room_number,
                        'type': lesson.classroom_assignment.room.get_room_type_display(),
                    }
                })
        return distribution
class StudentDayTimetableSerializer(serializers.Serializer):
    classroom = ClassSectionSerializer()
    sessions = SessionSerializer(many=True)
class StudentWeekTimetableSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        working_days = kwargs.pop('working_days', [])
        super().__init__(*args, **kwargs)

        for day in working_days:
            self.fields[day] = StudentDayTimetableSerializer(many=True)








