from rest_framework import serializers
from ...models import Standard, Classroom, Grade, User,Teacher,Subject

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
        read_only_fields = ['id', 'created_at', 'updated_at', 'class_id',]

    def validate(self, data):
        # The standard is already a Standard object, no need to query again
        if not isinstance(data['standard'], Standard):
            raise serializers.ValidationError("Invalid standard specified.")

        return data

        # Ensure the school (User) exists
       

        return data