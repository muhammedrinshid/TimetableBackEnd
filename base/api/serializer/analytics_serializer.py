from ...models import Teacher
from rest_framework import serializers


class TeacherDetailSerializer(serializers.ModelSerializer):
    working_sessions_in_a_week = serializers.IntegerField()  # Add this
    free_sessions_in_a_week = serializers.IntegerField()
    extra_loads_last_week = serializers.IntegerField()
    leaves_last_week = serializers.IntegerField()
    class Meta:
        model = Teacher
        fields = ['id', 'name', 'surname', 'profile_image', 'working_sessions_in_a_week', 'free_sessions_in_a_week','extra_loads_last_week','leaves_last_week']

class TeacherUtilizationSerializer(serializers.Serializer):
    chart_header_details = serializers.DictField()
    chart_details = TeacherDetailSerializer(many=True)
