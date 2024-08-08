from rest_framework import serializers
from ...models import Room
class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'room_number', 'capacity', 'occupied', 'room_type', 'school']
        read_only_fields = ['id', 'school']