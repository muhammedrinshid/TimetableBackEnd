from rest_framework import serializers
from ...models import Standard, Classroom, Grade, User, Teacher, Subject, ClassSubject, ClassSubjectSubject
from django.db import transaction

# Existing serializers

class StandardSerializer(serializers.ModelSerializer):
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all())

    class Meta:
        model = Standard
        fields = ['id', 'name', 'short_name', 'grade', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ClassroomLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ['id', 'name', 'division', 'subject_count']

class StandardLightSerializer(serializers.ModelSerializer):
    classrooms = ClassroomLightSerializer(many=True, read_only=True)

    class Meta:
        model = Standard
        fields = ['id', 'name', 'short_name', 'classrooms']

class GradeLightSerializer(serializers.ModelSerializer):
    standards = StandardLightSerializer(many=True, read_only=True)

    class Meta:
        model = Grade
        fields = ['id', 'name', 'short_name', 'standards']

class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'full_name', 'profile_image']

    def get_full_name(self, obj):
        return f"{obj.name} {obj.surname}" if obj.surname else obj.name

class SubjectWithTeachersSerializer(serializers.ModelSerializer):
    qualified_teachers = TeacherSerializer(source='available_teachers', many=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'qualified_teachers']

class ClassroomSerializer(serializers.ModelSerializer):
    standard = serializers.PrimaryKeyRelatedField(queryset=Standard.objects.all())

    class Meta:
        model = Classroom
        fields = ['id', 'name', 'standard', 'number_of_students', 'room_number', 
                  'class_id', 'created_at', 'updated_at', 'division']
        read_only_fields = ['id', 'created_at', 'updated_at', 'class_id']

    def validate(self, data):
        if not isinstance(data['standard'], Standard):
            raise serializers.ValidationError("Invalid standard specified.")
        return data

class SubjectTeacherSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    qualifiedTeachers = serializers.ListField(child=serializers.UUIDField())

class ClassSubjectSerializer(serializers.ModelSerializer):
    school = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class_room = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all())
    elective_or_core = serializers.ChoiceField(choices=['core', 'elective'])
    subjects = SubjectTeacherSerializer(many=True, write_only=True)

    class Meta:
        model = ClassSubject
        fields = ['school', 'class_room', 'name', 'elective_or_core', 'subjects', 'lessons_per_week']

    def create(self, validated_data):
        subjects_data = validated_data.pop('subjects')
        class_room = validated_data.pop('class_room')
        
        validated_data['class_room'] = class_room
        validated_data['elective_or_core'] = (validated_data.pop('elective_or_core') == 'elective')

        with transaction.atomic():
            class_subject = ClassSubject.objects.create(**validated_data)

            for subject_data in subjects_data:
                subject = Subject.objects.get(id=subject_data['id'])
                class_subject_subject = ClassSubjectSubject.objects.create(
                    school=class_subject.school,
                    class_subject=class_subject,
                    subject=subject
                )

                for teacher_id in subject_data['qualifiedTeachers']:
                    teacher = Teacher.objects.get(id=teacher_id)
                    class_subject_subject.assigned_teachers.add(teacher)

        return class_subject

# New serializers for retrieving detailed classroom data

class TeacherDetailSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    image = serializers.ImageField(source='profile_image', use_url=True)

    class Meta:
        model = Teacher
        fields = ['id', 'name', 'image']

    def get_name(self, obj):
        return f"{obj.name} {obj.surname}" if obj.surname else obj.name

class SubjectDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']

class ClassSubjectSubjectDetailSerializer(serializers.ModelSerializer):
    subject = SubjectDetailSerializer()
    alotted_teachers = TeacherDetailSerializer(source='assigned_teachers', many=True)

    class Meta:
        model = ClassSubjectSubject
        fields = ['subject', 'number_of_students', 'alotted_teachers']

class ElectiveGroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassSubject
        fields = ['id', 'name']

class ClassSubjectDetailSerializer(serializers.ModelSerializer):
    options = ClassSubjectSubjectDetailSerializer(source='class_subjects', many=True)
    elective_group = ElectiveGroupDetailSerializer(source='*', read_only=True)
    teacher = TeacherDetailSerializer(source='class_subjects.first.assigned_teachers', many=True, read_only=True)
    is_elective = serializers.BooleanField(source='elective_or_core')

    class Meta:
        model = ClassSubject
        fields = ['id', 'name', 'lessons_per_week', 'is_elective', 'elective_group', 'options', 'teacher']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.elective_or_core:
            data.pop('options', None)
            data.pop('elective_group', None)
        else:
            data.pop('teacher', None)
        return data

class ClassroomDetailSerializer(serializers.ModelSerializer):
    standard_name = serializers.CharField(source='standard.name')
    room_no = serializers.CharField(source='room_number', allow_null=True)
    lessons_assigned_subjects = serializers.SerializerMethodField()
    subjects_assigned_teacher = serializers.SerializerMethodField()
    total_subjects = serializers.SerializerMethodField()
    subject_data = ClassSubjectDetailSerializer(source='class_subjects', many=True)

    class Meta:
        model = Classroom
        fields = ['id', 'name', 'standard_name', 'division', 'room_no', 'lessons_assigned_subjects',
                  'subjects_assigned_teacher', 'total_subjects', 'subject_data']

    def get_lessons_assigned_subjects(self, obj):
        return sum(cs.lessons_per_week for cs in obj.class_subjects.all())

    def get_subjects_assigned_teacher(self, obj):
        return sum(1 for cs in obj.class_subjects.all() if cs.class_subjects.filter(assigned_teachers__isnull=False).exists())

    def get_total_subjects(self, obj):
        return obj.class_subjects.count()