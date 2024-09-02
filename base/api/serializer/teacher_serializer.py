from rest_framework import serializers
from ...models import Teacher, Subject, Grade
from .user_serializer import SubjectSerializer,GradeSerializer


class TeacherSerializer(serializers.ModelSerializer):
    qualified_subjects = serializers.ListField(child=serializers.CharField(), write_only=True)
    grades = serializers.ListField(child=serializers.UUIDField(), write_only=True)
    qualified_subjects_display = SubjectSerializer(source='qualified_subjects', many=True, read_only=True,)
    grades_display = GradeSerializer(source='grades', many=True, read_only=True)
    class Meta:
        model = Teacher
        fields = [
            'id', 'name', 'surname', 'email', 'phone',
            'min_lessons_per_week', 'max_lessons_per_week',
            'teacher_id', 'profile_image', 'qualified_subjects', 'grades', 'qualified_subjects_display', 'grades_display',
        ]
        read_only_fields = ['id', 'teacher_id', 'created_at', 'updated_at']

    def create(self, validated_data):
        qualified_subjects = validated_data.pop('qualified_subjects', [])
        grades = validated_data.pop('grades', [])
        teacher = Teacher.objects.create(**validated_data)
        
        school = self.context['request'].user  # Assuming the user has a school attribute
        for subject_name in qualified_subjects:
            subject, _ = Subject.objects.get_or_create(name=subject_name, school=school)
            teacher.qualified_subjects.add(subject)
        
        teacher.grades.set(Grade.objects.filter(id__in=grades))
        
        return teacher

    def update(self, instance, validated_data):
        
        qualified_subjects = validated_data.pop('qualified_subjects', None)
        grades = validated_data.pop('grades', None)
        
        instance = super().update(instance, validated_data)
        
        if qualified_subjects is not None:
            instance.qualified_subjects.clear()
            school = self.context['request'].user
            for subject_name in qualified_subjects:
                subject, _ = Subject.objects.get_or_create(name=subject_name, school=school)
                instance.qualified_subjects.add(subject)
        
        if grades is not None:
            instance.grades.set(Grade.objects.filter(id__in=grades))
        
        return instance