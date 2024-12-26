from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist

import json



from ...models import Grade,Standard,ClassSubject,ElectiveGroup,Room

from ..serializer.elective_group_serializer import GradeWithElectiveGroupsSerializer,ElectiveSubjectSerializer,ElectiveGroupSerializer



@api_view(["GET","PUT"])
@permission_classes([IsAuthenticated])
def get_elective_groups(request):
    user=request.user
    if request.method=="GET":
        grades_with_elective_groups=Grade.objects.filter(school=user).prefetch_related(
            Prefetch("standards",queryset=Standard.objects.prefetch_related(
                Prefetch("electives_groups",queryset=ElectiveGroup.objects.prefetch_related(
                    Prefetch("class_subjects",ClassSubject.objects.filter(elective_or_core=True)
                            .prefetch_related("subjects","class_room__standard")
                            )
                ))
            ))
        )
        serializer = GradeWithElectiveGroupsSerializer(grades_with_elective_groups, many=True)
        return Response(serializer.data)
    elif request.method =="PUT":
        try:
        # Parse the incoming JSON data
            data = request.data
            groups = data.get("groups", {})

            for group_id, class_subject_ids in groups.items():
                # Get ElectiveGroup for the authenticated user's school
                elective_group = ElectiveGroup.objects.filter(
                    id=group_id, 
                    school=request.user
                ).first()
                if not elective_group:
                    return Response({"error": f"ElectiveGroup {group_id} not found or not authorized."}, status=status.HTTP_404_NOT_FOUND)

                for class_subject_id in class_subject_ids:
                    # Get ClassSubject for the authenticated user's school
                    class_subject = ClassSubject.objects.filter(
                        id=class_subject_id, 
                        school=request.user
                    ).first()
                    if not class_subject:
                        return Response({"error": f"ClassSubject {class_subject_id} not found or not authorized."}, status=status.HTTP_404_NOT_FOUND)

                    # Assign the ElectiveGroup only if it's not already assigned
                    if class_subject.elective_group != elective_group:
                        class_subject.elective_group = elective_group
                        class_subject.save()

            return Response({"message": "Elective groups assigned successfully."}, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON data."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_standard_elective_subjects(request,pk=None):
    if pk is not None:
        try:
          standard=Standard.objects.get(id=pk,school=request.user)
        except Standard.DoesNotExist:
            return Response({"error": "Standard not found"}, status=404)
        elective_subjects=ClassSubject.objects.filter(class_room__standard=standard,elective_or_core=True,elective_group=None)
        serializer=ElectiveSubjectSerializer(elective_subjects,many=True)
        return Response(serializer.data)

      
    else:
        print("heree")
        elective_subjects=ClassSubject.objects.filter(elective_or_core=True,elective_group=None)
        serializer=ElectiveSubjectSerializer(elective_subjects,many=True)
        return Response(serializer.data)
        
   
    
    
    
@api_view(['POST', 'PUT','DELETE'])
@permission_classes([IsAuthenticated])
def create_or_update_elective_group(request, pk=None):
    """
    Creates a new Elective Group or updates an existing one.
    Expects `standard_id`, `name`, and `preferred_rooms` in the request body.
    """
    
    if pk is not None:
        try:
            elective_group = ElectiveGroup.objects.get(id=pk)
        except ElectiveGroup.DoesNotExist:
            return Response({"error": "Elective Group not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'PUT':
            # Get new data from request
            name = request.data.get('name', elective_group.name)
            preferred_rooms = request.data.get('preferred_rooms', [])

            # Update name
            elective_group.name = name

            # Clear and update preferred rooms
            elective_group.preferred_rooms.clear()  # Clear existing preferred rooms
            for room_id in preferred_rooms:
                try:
                    room = Room.objects.get(id=room_id)
                    elective_group.preferred_rooms.add(room)
                except Room.DoesNotExist:
                    return Response({"error": f"Room with id {room_id} not found."}, status=status.HTTP_400_BAD_REQUEST)

            # Save the updated group
            elective_group.save()

            # Serialize the updated elective group and return it
            serializer = ElectiveGroupSerializer(elective_group)
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.method == "DELETE":
            elective_group.delete()
            return Response({"message": "Elective Group deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    if request.method == 'POST':
        standard_id = request.data.get('standard_id')
        name = request.data.get('name')
        preferred_rooms = request.data.get('preferred_rooms', [])

        # Validate that the standard_id exists
        try:
            standard = Standard.objects.get(id=standard_id)
        except Standard.DoesNotExist:
            return Response({"error": "Standard not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the Elective Group
        elective_group = ElectiveGroup.objects.create(
            name=name,
            standard=standard,
            school=request.user  # Assuming you want to associate the logged-in user with the school
        )

        # Add preferred rooms (many-to-many relationship)
        for room_id in preferred_rooms:
            try:
                room = Room.objects.get(id=room_id)
                elective_group.preferred_rooms.add(room)
            except Room.DoesNotExist:
                return Response({"error": f"Room with id {room_id} not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Save the group
        elective_group.save()

        # Serialize the created elective group and return it
        serializer = ElectiveGroupSerializer(elective_group)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])    
def remove_elective_group_connection(request,pk=None):
    print("hix")
    if pk is not None:
        try:
            elective_subject=ClassSubject.objects.get(id=pk,school=request.user)
            elective_subject.elective_group=None
            elective_subject.save()
            return Response(
                  {'success': True, 'message': 'Elective group connection successfully removed.'},
                status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(
                {'success': False, 'message': 'Elective subject not found or does not belong to your school.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Handle any other exceptions
            return Response(
                {'success': False, 'message': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 
    return Response(
        {'success': False, 'message': 'No valid primary key (pk) provided.'},
        status=status.HTTP_400_BAD_REQUEST
    )
