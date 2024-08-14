from rest_framework import serializers
from ...time_table_models import Timetable

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