from rest_framework import serializers
from ...models import Room

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['name', 'room_number', 'room_type','id']
        
class ElectiveSubjectSerializer(serializers.Serializer):
    elective_subject_name = serializers.CharField(source='name')
    lessons_per_week = serializers.IntegerField()
    classroom_name = serializers.SerializerMethodField()
    classroom_id = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    elective_subject_id=serializers.UUIDField(source="id")
    standard_id=serializers.SerializerMethodField()
    def get_classroom_name(self, obj):
        return f"{obj.class_room.standard.short_name}{obj.class_room.division}"
    def get_classroom_id(self, obj):
        return obj.class_room.id

    def get_options(self, obj):
        return [subject.name[:3].upper() for subject in obj.subjects.all()]
    
    def get_standard_id(self, obj):
        return obj.class_room.standard.id


class ElectiveGroupSerializer(serializers.Serializer):
    group_name=serializers.CharField(source="name")
    group_id=serializers.UUIDField(source="id")
    elective_subjects=ElectiveSubjectSerializer(source="class_subjects",many=True)
    preferred_rooms=RoomSerializer(many=True)

class StandardSerializer(serializers.Serializer):
    standard_short_name=serializers.CharField(source="short_name")
    standard_name=serializers.CharField(source="name")
    standard_id=serializers.UUIDField(source="id")
    electives_groups=ElectiveGroupSerializer(many=True)
    

class GradeWithElectiveGroupsSerializer(serializers.Serializer):
    grade_name=serializers.CharField(source="name")
    grade_short_name=serializers.CharField(source="short_name")
    grade_id=serializers.UUIDField(source="id")
    standards=StandardSerializer( many=True)