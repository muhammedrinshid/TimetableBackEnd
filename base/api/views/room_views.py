from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ...models import Room
from rest_framework.decorators import api_view,permission_classes
from ..serializer.room_serializer import RoomSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_non_occupied_rooms(request):
    non_occupied_rooms = Room.objects.filter(school=request.user,room_type='CLASSROOM' ,occupied=False)
    serializer = RoomSerializer(non_occupied_rooms, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def room_manager(request, pk=None):
    if request.method == 'GET':
        if pk:
            try:
                room = Room.objects.get(pk=pk, school=request.user)
                serializer = RoomSerializer(room)
                return Response(serializer.data)
            except Room.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            rooms = Room.objects.filter(school=request.user)
            serializer = RoomSerializer(rooms, many=True)
            return Response(serializer.data)

    elif request.method == 'POST':
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            room = serializer.save(school=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method in ['PUT', 'DELETE']:
        if not pk:
            return Response({"error": "Room ID is required for update and delete operations."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            room = Room.objects.get(pk=pk, school=request.user)
        except Room.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == 'PUT':
            serializer = RoomSerializer(room, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            room.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def school_rooms(request):
    rooms = Room.objects.filter(school=request.user)
    serializer = RoomSerializer(rooms, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_room_number_availability(request,room_number=None):
    
    
    if not room_number:
        return Response({"error": "Room number is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    is_available = not Room.objects.filter(room_number=room_number, school=request.user).exists()
    
    return Response({
        "room_number": room_number,
        "is_available": is_available
    })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def school_rooms_except_classrooms(request):
    rooms = Room.objects.filter(school=request.user).exclude(room_type="CLASSROOM")
    serializer = RoomSerializer(rooms, many=True)
    return Response(serializer.data)