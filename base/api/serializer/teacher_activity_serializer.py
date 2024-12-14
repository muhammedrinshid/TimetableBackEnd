from rest_framework import serializers
from ...models import Teacher, Subject, Grade
from .class_room_serializer import SimpleTeacherSerializer



class TeacherActivitySummarySerializer(serializers.Serializer):
    teacher = SimpleTeacherSerializer()
    leaves_count = serializers.IntegerField()
    extra_loads_count = serializers.IntegerField()
    leave_days_count = serializers.IntegerField()
    extra_load_days_count = serializers.IntegerField()
