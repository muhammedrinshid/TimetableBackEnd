from rest_framework import serializers
from ...models import Standard, Classroom, Grade, User, Teacher, Subject, ClassSubject, ClassSubjectSubject,ElectiveGroup,Room
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
        fields = ['id', 'name', 'division', 'lessons_assigned_subjects']

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
        fields = ['id', 'name', 'standard', 'number_of_students', 
                  'class_id', 'created_at', 'updated_at', 'division','room']
        read_only_fields = ['id', 'created_at', 'updated_at', 'class_id']

    def validate(self, data):
        if 'standard' in data and not isinstance(data['standard'], Standard):
            raise serializers.ValidationError("Invalid standard specified.")
        return data

class SubjectTeacherSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    qualifiedTeachers = serializers.ListField(child=serializers.UUIDField())
    preferedRooms = serializers.ListField(child=serializers.UUIDField(), required=False)  # Add this line

class ClassSubjectSerializer(serializers.ModelSerializer):
    school = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class_room = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all())
    elective_or_core = serializers.ChoiceField(choices=['core', 'elective'])
    subjects = SubjectTeacherSerializer(many=True, write_only=True)

    class Meta:
        model = ClassSubject
        fields = ['school', 'class_room', 'name', 'elective_or_core', 'subjects', 'lessons_per_week','multi_block_lessons']

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
                    
                
                if 'preferedRooms' in subject_data:  # Check if the key exists
                    for room_id in subject_data['preferedRooms']:
                        room = Room.objects.get(id=room_id)
                        class_subject_subject.preferred_rooms.add(room)

        return class_subject

# New serializers for retrieving detailed classroom data

class ElectiveGroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectiveGroup
        fields = ['id', 'name']

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'room_number', 'capacity', 'occupied', 'room_type', 'school']
        read_only_fields = ['id', 'school']


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
    allotted_teachers = TeacherDetailSerializer(source='assigned_teachers', many=True)
    preferred_rooms = RoomSerializer( many=True,)

    class Meta:
        model = ClassSubjectSubject
        fields = ['subject', 'number_of_students', 'allotted_teachers','preferred_rooms']



class ClassSubjectDetailSerializer(serializers.ModelSerializer):
    options = ClassSubjectSubjectDetailSerializer(source='class_subject_subjects', many=True)
    elective_group = ElectiveGroupDetailSerializer(read_only=True)
    teacher = TeacherDetailSerializer(source='class_subject_subjects.first.assigned_teachers', many=True, read_only=True)
    special_rooms = RoomSerializer(source='class_subject_subjects.first.preferred_rooms', many=True, read_only=True)
    is_elective = serializers.BooleanField(source='elective_or_core')

    class Meta:
        model = ClassSubject
        fields = ['id', 'name', 'lessons_per_week', 'is_elective', 'elective_group', 'options', 'teacher','special_rooms','multi_block_lessons']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.elective_or_core:
            data.pop('elective_group', None)
            if data['options']:
                data['subjectId'] = data['options'][0]['subject']['id']
        else:
            data.pop('teacher', None)
        return data
    

class ClassroomDetailSerializer(serializers.ModelSerializer):
    standard_name = serializers.CharField(source='standard.name')
    standard_short_name = serializers.CharField(source='standard.short_name')
    room = RoomSerializer( allow_null=True)
    lessons_assigned_subjects = serializers.SerializerMethodField()
    subjects_assigned_teacher = serializers.SerializerMethodField()
    total_subjects = serializers.SerializerMethodField()
    subject_data = ClassSubjectDetailSerializer(source='class_subjects', many=True)

    class Meta:
        model = Classroom
        fields = ['id', 'name', 'standard_name','standard_short_name', 'division', 'room', 'lessons_assigned_subjects',
                  'subjects_assigned_teacher', 'total_subjects', 'subject_data','number_of_students']

    def get_lessons_assigned_subjects(self, obj):
        return sum(cs.lessons_per_week for cs in obj.class_subjects.all())

    def get_subjects_assigned_teacher(self, obj):
        return sum(1 for cs in obj.class_subjects.all() if cs.class_subject_subjects.filter(assigned_teachers__isnull=False).exists())

    def get_total_subjects(self, obj):
        return obj.class_subjects.count()
    
    
    

class ElectiveGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectiveGroup
        fields = ['id', 'name', 'standard']

class ClassSubjectUpdateSerializer(serializers.Serializer):
    classroom_id = serializers.UUIDField()
    division = serializers.CharField()
    id = serializers.UUIDField()
    name = serializers.CharField()

class ElectiveGroupCreateSerializer(serializers.Serializer):
    groupName = serializers.CharField()
    groupId = serializers.CharField(required=False)
    standardId = serializers.UUIDField()
    divisions = ClassSubjectUpdateSerializer(many=True)
    preferredRooms = serializers.ListField(  
        child=serializers.UUIDField(),
        required=False
    )
    
    
    
    
    
    
    
    
    
    
class ClassSubjectLightSerializer(serializers.ModelSerializer):
    classroom_id = serializers.UUIDField(source="class_room.id",read_only=True)

    class Meta:
        model = ClassSubject
        fields = ['id', 'name','classroom_id']




class ElectiveGroupGetSerializer(serializers.ModelSerializer):
    preferred_rooms = serializers.SerializerMethodField()

    class Meta:
        model = ElectiveGroup
        fields = ['id', 'name', 'standard', 'school', 'preferred_rooms']

    def get_preferred_rooms(self, obj):
        return [str(room.id) for room in obj.preferred_rooms.all()]
    
    
class ClassroomElectiveSerializer(serializers.ModelSerializer):
    elective_class_subjects = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['id', 'division', 'elective_class_subjects']

    def get_elective_class_subjects(self, obj):
        elective_subjects = obj.class_subjects.filter(elective_or_core=True)
        return ClassSubjectLightSerializer(elective_subjects, many=True).data

class ElectiveSubjectAddSerializer(serializers.Serializer):
    existing_elective_groups = ElectiveGroupGetSerializer(many=True, read_only=True)
    classrooms = ClassroomElectiveSerializer(many=True, read_only=True)
    room = RoomSerializer(required=False, allow_null=True)

    class Meta:
        model = Classroom
        fields = ['room', 'number_of_students', 'name']

    def validate_number_of_students(self, value):
        if value < 0:
            raise serializers.ValidationError("Number of students cannot be negative.")
        return value

    def update(self, instance, validated_data):
        room_data = validated_data.pop('room', None)
        if room_data is not None:
            if room_data == {}:
                instance.room = None
            else:
                room_number = room_data.get('room_number')
                try:
                    room = Room.objects.get(room_number=room_number)
                except Room.DoesNotExist:
                    room = Room.objects.create(
                        name=room_data.get('name', f"{instance.name} Room"),
                        room_number=room_number,
                        capacity=room_data.get('capacity', validated_data.get('number_of_students', instance.number_of_students)),
                        school=self.context['request'].user
                    )
                instance.room = room
        
        return super().update(instance, validated_data)
    
    
    

class ClassSubjectOptionSerializer(serializers.Serializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())
    number_of_students = serializers.IntegerField()
    assigned_teachers = serializers.PrimaryKeyRelatedField(many=True, queryset=Teacher.objects.all())
    preferred_rooms = serializers.PrimaryKeyRelatedField(many=True, queryset=Room.objects.all())

    

class ClassSubjectUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    lessons_per_week = serializers.IntegerField(required=False)
    subjects = ClassSubjectOptionSerializer(many=True, write_only=True)

    class Meta:
        model = ClassSubject
        fields = ['name', 'lessons_per_week', 'subjects']

    def validate(self, data):
        if 'subjects' not in data:
            raise serializers.ValidationError("Subjects field is required.")

        instance = self.instance
        subjects_data = data.get('subjects', [])

        # Check if this is an elective subject
        if instance and instance.elective_or_core:
            total_students = sum(subject.get('number_of_students', 0) for subject in subjects_data)
            if total_students > instance.class_room.number_of_students:
                raise serializers.ValidationError(
                    "For elective subjects, total number of students must be less than or equal to the number of students in the classroom."
                )

        # Validate core subjects have at most one subject
        if instance and not instance.elective_or_core and len(subjects_data) > 1:
            raise serializers.ValidationError('Core subjects must have at most one subject.')

        return data


    def update(self, instance, validated_data):
        with transaction.atomic():
            if instance.elective_or_core:
                instance.name = validated_data.get('name', instance.name)
            
            instance.lessons_per_week = validated_data.get('lessons_per_week', instance.lessons_per_week)
            instance.save()

            # Delete all current options
            instance.class_subject_subjects.all().delete()

            # Create new options
            subjects_data = validated_data.pop('subjects', [])
            for subject_data in subjects_data:
                try:
                    class_subject_subject = ClassSubjectSubject.objects.create(
                        school=instance.school,
                        class_subject=instance,
                        subject=subject_data['subject'],
                        number_of_students=subject_data['number_of_students']
                    )
                    class_subject_subject.assigned_teachers.set(subject_data['assigned_teachers'])
                    class_subject_subject.preferred_rooms.set(subject_data['preferred_rooms'])
                except KeyError as e:
                    raise serializers.ValidationError(f"Missing required field: {str(e)}")

        return instance