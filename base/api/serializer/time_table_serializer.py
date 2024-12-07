from rest_framework import serializers
from ...time_table_models import Timetable
from rest_framework import serializers
from ...models import  Teacher, Room, Subject, Classroom
from ...time_table_models import Timetable,  Lesson,LessonClassSection,Tutor,ClassSection,TimeTableDaySchedule,DayTutor,DayClassSection,DayLesson,DayLessonClassSection,DayStandardLevel,TeacherActivityLog
from .user_serializer import SubjectSerializer,GradeSerializer
from uuid import uuid4
from django.utils import timezone
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
    standard_id = serializers.CharField(source='class_section.classroom.standard.id')
    division = serializers.CharField(source='class_section.classroom.division')
    id=serializers.UUIDField(source='class_section.classroom.id')
    number_of_students = serializers.IntegerField()

    class Meta:
        model = LessonClassSection
        fields = ['id','standard', 'division', 'number_of_students','standard_id']
        
        
class TeacherSessionSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='course.name')
    subject_id = serializers.UUIDField(source='course.subject.id')
    type = serializers.SerializerMethodField()
    elective_subject_name = serializers.CharField()
    room = RoomSerializer(source='classroom_assignment.room')
    class_details = ClassDetailsSerializer(source='lessonclasssection_set', many=True)
    session_key=serializers.SerializerMethodField()
    lesson_id=serializers.UUIDField(source='id')
    class Meta:
        model = Lesson
        fields = ['subject','subject_id', 'type', 'elective_subject_name', 'room', 'class_details','elective_group_id','session_key','lesson_id']

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
    profile_image = serializers.SerializerMethodField()  # Use a custom method to handle the URL
    surname = serializers.CharField(source='teacher.surname')
    teacher_id = serializers.CharField(source='teacher.teacher_id')
    id = serializers.CharField(source='teacher.id')
    qualified_subjects = SubjectSerializer(source='teacher.qualified_subjects', many=True, read_only=True)

    class Meta:
        model = Tutor
        fields = ['id', 'name', 'profile_image', 'surname', 'teacher_id', 'qualified_subjects']

    def get_profile_image(self, obj):
        # Check if there is a profile image and return its URL, otherwise   return None or a default URL
        profile_image = obj.teacher.profile_image
        if profile_image:
            return profile_image.url
        return None  # Or you can return a default image URL if preferred
    

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


 
 
 
 
 
 
 
 
 
 
 
 
 
class ClassDetailsSerializerForSpecialDay(serializers.ModelSerializer):
    standard = serializers.CharField(source='class_section.classroom.standard.short_name')
    standard_id = serializers.CharField(source='class_section.classroom.standard.id')
    division = serializers.CharField(source='class_section.classroom.division')
    id=serializers.UUIDField(source='class_section.classroom.id')
    number_of_students = serializers.IntegerField()

    class Meta:
        model = DayLessonClassSection
        fields = ['id','standard', 'division', 'number_of_students','standard_id']
        
    
 
 
 
 
class TeacherSessionSerializerForSpecificDay(serializers.ModelSerializer):
    subject = serializers.CharField(source='course.name')
    subject_id = serializers.UUIDField(source='course.subject.id')
    type = serializers.SerializerMethodField()
    elective_subject_name = serializers.CharField()
    room = RoomSerializer(source='classroom_assignment.room')
    class_details = ClassDetailsSerializerForSpecialDay(source='class_section_assignments', many=True)
    session_key=serializers.SerializerMethodField()
    lesson_id=serializers.UUIDField(source='id')
    lesson_level = serializers.SerializerMethodField()
    class Meta:
        model = DayLesson
        fields = ['subject','subject_id', 'type', 'elective_subject_name', 'room', 'class_details','elective_group_id','session_key','lesson_id','lesson_level']

    def get_type(self, obj):
        return 'Elective' if obj.is_elective else 'Core'
    def get_lesson_level(self, obj):
        first_class_section = obj.class_section_assignments.first()
        if first_class_section:
            grade = first_class_section.class_section.classroom.standard.grade

            # Serialize the grade object
            grade_serializer = GradeSerializer(grade)
            return grade_serializer.data  # Return the serialized data
        return None

    def to_representation(self, instance):
        if instance is None:
            # Return a dictionary with all fields set to None
            return {field: None for field in self.Meta.fields}
        return super().to_representation(instance)
    def get_session_key(self, obj):
        return str(uuid4())  # Generate a new UUID for each instance

class InstructorSerializerForSpecificDay(serializers.ModelSerializer):
    name = serializers.CharField(source='teacher.name')
    profile_image = serializers.SerializerMethodField()
    surname = serializers.CharField(source='teacher.surname')
    teacher_id = serializers.CharField(source='teacher.teacher_id')
    id = serializers.CharField(source='teacher.id')
    qualified_subjects = SubjectSerializer(source='teacher.qualified_subjects', many=True, read_only=True)
    qualified_levels = GradeSerializer(source='teacher.grades', many=True, read_only=True)
    
    # New fields for activity logs
    last_week_leaves = serializers.SerializerMethodField()
    last_month_leaves = serializers.SerializerMethodField()
    academic_year_leaves = serializers.SerializerMethodField()
    
    last_week_extra_loads = serializers.SerializerMethodField()
    last_month_extra_loads = serializers.SerializerMethodField()
    academic_year_extra_loads = serializers.SerializerMethodField()
    
    class Meta:
        model = DayTutor
        fields = [
            'id', 'name', 'profile_image', 'surname', 'teacher_id', 'qualified_levels',
            'qualified_subjects', 'last_week_leaves', 'last_month_leaves', 
            'academic_year_leaves', 'last_week_extra_loads', 
            'last_month_extra_loads', 'academic_year_extra_loads',
        ]

    def get_profile_image(self, obj):
        profile_image = obj.teacher.profile_image
        return profile_image.url if profile_image else None

    def _get_activity_count(self, obj, activity_type, start_date, end_date):
        """
        Helper method to count activities for a specific teacher within a date range
        
        :param obj: DayTutor instance
        :param activity_type: 'leave' or 'extra_load'
        :param start_date: Start date for filtering
        :param end_date: End date for filtering
        :return: Count of activities
        """
        return TeacherActivityLog.objects.filter(
            primary_teacher=obj.teacher,
            activity_type=activity_type,
            date__range=[start_date, end_date]
        ).count()

    def _get_date_from_context(self):
        """
        Retrieve the reference date from the serializer context
        
        :return: Reference date (defaults to today if not provided)
        """
        return self.context.get('specific_date', timezone.now().date())

    def get_last_week_leaves(self, obj):
        """Count leaves in the last 7 days"""
        reference_date = self._get_date_from_context()
        start_date = reference_date - timezone.timedelta(days=7)
        return self._get_activity_count(obj, 'leave', start_date, reference_date)

    def get_last_month_leaves(self, obj):
        """Count leaves in the last 30 days"""
        reference_date = self._get_date_from_context()
        start_date = reference_date - timezone.timedelta(days=30)
        return self._get_activity_count(obj, 'leave', start_date, reference_date)

    def get_academic_year_leaves(self, obj):
        """Count leaves in the current academic year"""
        # Fetch academic year dates from context
        start_date = self.context.get('academic_year_start')
        end_date = self.context.get('academic_year_end')
        
        # Fallback if dates not provided
        if not start_date or not end_date:
            # You might want to raise an exception or log a warning
            return 0
        
        return self._get_activity_count(obj, 'leave', start_date, end_date)

    def get_last_week_extra_loads(self, obj):
        """Count extra loads in the last 7 days"""
        reference_date = self._get_date_from_context()
        start_date = reference_date - timezone.timedelta(days=7)
        return self._get_activity_count(obj, 'extra_load', start_date, reference_date)

    def get_last_month_extra_loads(self, obj):
        """Count extra loads in the last 30 days"""
        reference_date = self._get_date_from_context()
        start_date = reference_date - timezone.timedelta(days=30)
        return self._get_activity_count(obj, 'extra_load', start_date, reference_date)

    def get_academic_year_extra_loads(self, obj):
        """Count extra loads in the current academic year"""
        # Fetch academic year dates from context
        start_date = self.context.get('academic_year_start')
        end_date = self.context.get('academic_year_end')
        
        # Fallback if dates not provided
        if not start_date or not end_date:
            # You might want to raise an exception or log a warning
            return 0
        
        return self._get_activity_count(obj, 'extra_load', start_date, end_date)



class TeacherDayTimetableSerializerForSpecificDay(serializers.Serializer):
    instructor = serializers.SerializerMethodField()
    sessions = serializers.ListField(child=TeacherSessionSerializerForSpecificDay(many=True))
    def get_instructor(self, obj):
        # Extract specific_date and academic_year details
        specific_date = self.context.get('specific_date')
        academic_year_start = self.context.get('academic_year_start')
        academic_year_end = self.context.get('academic_year_end')

        # Pass them to the nested serializer
        return InstructorSerializerForSpecificDay(
            obj.get('instructor'),
            context={
                'specific_date': specific_date,
                'academic_year_start': academic_year_start,
                'academic_year_end': academic_year_end
            }
        ).data










class ClassSectionSerializerForSpecificDay(serializers.ModelSerializer):
    standard = serializers.CharField(source='classroom.standard.short_name')
    room = RoomSerializer(source='classroom.room')
    total_students = serializers.CharField(source='classroom.number_of_students')
    class_id=serializers.CharField(source='classroom.class_id')
    id=serializers.UUIDField(source='classroom.id')
    class Meta:
        model = DayClassSection
        fields = ['id','standard', 'division', 'room', 'total_students','class_id']




class StudentSessionSerializerForSpecificDay(serializers.Serializer):
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    elective_id = serializers.SerializerMethodField()  # Use SerializerMethodField here
    class_distribution = serializers.SerializerMethodField()
    session_key=serializers.SerializerMethodField()
    class_id=serializers.SerializerMethodField()
    

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

        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return None
        
        first_lesson = obj[0]
        
        
        # Return the elective_group_id if it's an elective lesson, else None
        return first_lesson.elective_group_id if first_lesson.is_elective and first_lesson.elective_group_id else None
    def get_session_key(self, obj):
        return str(uuid4())  # Generate a new UUID for each instance

    def get_class_distribution(self, obj):
        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return []
        
        distribution = []
        for lesson in obj:
            current_class_section = self.context.get('class_section')
            
            try:
                lcs = DayLessonClassSection.objects.get(day_lesson=lesson, class_section=current_class_section)
                distribution.append({
                    'subject': lesson.course.name,
                    'lesson_id':lesson.id,
                    'teacher': {
                        'name': f"{lesson.allotted_teacher.teacher.name} {lesson.allotted_teacher.teacher.surname}".strip(),
                        'profile_image': lesson.allotted_teacher.teacher.profile_image.url if lesson.allotted_teacher.teacher.profile_image else None,
                        'id': lesson.allotted_teacher.teacher.id,
                    },
                    'number_of_students_from_this_class': lcs.number_of_students,
                    'room': {
                        'name': lesson.classroom_assignment.room.name,
                        'room_number': lesson.classroom_assignment.room.room_number,
                        'room_type': lesson.classroom_assignment.room.get_room_type_display(),
                        'id': lesson.classroom_assignment.room.id,
                    }
                })
            except DayLessonClassSection.DoesNotExist:
                pass

        return distribution
    def get_class_id(self,obj):
        class_section=self.context.get("class_section")
        return class_section.classroom.class_id if class_section.classroom else None
    
   
class StudentDayTimetableSerializerForSpecificDay(serializers.Serializer):
    classroom = ClassSectionSerializerForSpecificDay()
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
                        StudentSessionSerializerForSpecificDay(
                            lesson_group, 
                            context={'class_section': obj['classroom']}
                        ).data
                    )
            formatted_sessions.append(period_data)
            
        return formatted_sessions
    





















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
    session_key=serializers.SerializerMethodField()
    class_id=serializers.SerializerMethodField()
    

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

        if not obj or (isinstance(obj, list) and len(obj) == 0):
            return None
        
        first_lesson = obj[0]
        
        
        # Return the elective_group_id if it's an elective lesson, else None
        return first_lesson.elective_group_id if first_lesson.is_elective and first_lesson.elective_group_id else None
    def get_session_key(self, obj):
        return str(uuid4())  # Generate a new UUID for each instance

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
                    'lesson_id':lesson.id,
                    'teacher': {
                        'name': f"{lesson.allotted_teacher.teacher.name} {lesson.allotted_teacher.teacher.surname}".strip(),
                        'profile_image': lesson.allotted_teacher.teacher.profile_image.url if lesson.allotted_teacher.teacher.profile_image else None,
                        'id': lesson.allotted_teacher.teacher.id,
                    },
                    'number_of_students_from_this_class': lcs.number_of_students,
                    'room': {
                        'name': lesson.classroom_assignment.room.name,
                        'room_number': lesson.classroom_assignment.room.room_number,
                        'room_type': lesson.classroom_assignment.room.get_room_type_display(),
                        'id': lesson.classroom_assignment.room.id,
                    }
                })
            except LessonClassSection.DoesNotExist:
                pass

        return distribution
    def get_class_id(self,obj):
        class_section=self.context.get("class_section")
        return class_section.classroom.class_id if class_section.classroom else None
    
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

    

class TimeTableDayScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTableDaySchedule
        fields = ['day', 'teaching_slots']





