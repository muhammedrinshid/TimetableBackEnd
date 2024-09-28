from rest_framework import serializers
from ...models import User,Level,Subject,UserConstraintSettings



class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['name', 'short_name','id']
        
        
        
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name', 'id']
        
class UserSerializer(serializers.ModelSerializer):
    working_days = serializers.ListField(required=False)
    profile_image = serializers.ImageField(read_only=True)  # Changed to read-only
    levels = LevelSerializer(many=True, read_only=True, source='level_set')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'school_name', 'school_id', 'address',
            'city', 'state', 'country', 'postal_code', 'profile_image', 'working_days',
            'teaching_slots', 'average_students_allowed_in_a_class', 'period_name',
            'all_classes_subject_assigned_atleast_one_teacher',
            'all_classes_assigned_subjects', 
            'levels'
        ]
        read_only_fields = ['id', 'school_id', 'email', 'profile_image']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.profile_image:
            representation['profile_image'] = instance.profile_image.url
        return representation
    
    
class UserConstraintSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConstraintSettings
        exclude = ['user']  # Exclude user field as it will be set automatically