




import logging


from rest_framework import status,serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ...models import Standard, Classroom, Grade,Subject,Teacher,ClassSubject,ClassSubjectSubject,ElectiveGroup,Room
from rest_framework.decorators import api_view,permission_classes
from ..serializer.class_room_serializer import StandardSerializer,ElectiveSubjectAddSerializer,ClassSubjectUpdateSerializer,RoomSerializer,ElectiveGroupGetSerializer,ElectiveGroupCreateSerializer, ClassroomSerializer,GradeLightSerializer,SubjectWithTeachersSerializer,ClassSubjectSerializer,ClassroomDetailSerializer
from django.db import transaction
from django.db.models import Prefetch
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
logger = logging.getLogger(__name__)


# helper function to get latest divison
def get_next_division_name(existing_divisions):
    # If there are no existing divisions, start with 'A'
    if not existing_divisions:
        return 'A'

    for i in range(26):
        div_name = chr(65 + i)  # A to Z
        if div_name not in existing_divisions:
            return div_name

    # If all single letters are used, start with AA, AB, etc.
    prefix = 'A'
    while True:
        for i in range(26):
            div_name = prefix + chr(65 + i)
            if div_name not in existing_divisions:
                return div_name
        prefix = chr(ord(prefix) + 1)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_grades_standards_classrooms(request):
    
    grades = Grade.objects.filter(school=request.user).prefetch_related(
        'standards',
        'standards__classrooms'
    )
    serializer = GradeLightSerializer(grades, many=True)
    return Response(serializer.data)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_new_division(request):
    standard_id=request.data.get('standard_id')
    
    try:
        standard=Standard.objects.get(school=request.user,id=standard_id)
    except Standard.DoesNotExist:
        return Response({"error":"standard not found"},status=status.HTTP_404_NOT_FOUND)
    existing_divisions=standard.classrooms.values_list("division",flat=True)
    new_division_name=get_next_division_name(existing_divisions)
    class_room_data={
        "name":f'Division {new_division_name}',
        'standard':standard.id,
        'division': new_division_name,

        
    }
    classroom_serializer=ClassroomSerializer(data=class_room_data)
    if classroom_serializer.is_valid():
        classroom=classroom_serializer.save(school=request.user)
        return Response(data=classroom_serializer.data,status=status.HTTP_201_CREATED)
    else:
        return Response(classroom_serializer.errors, status=status.HTTP_400_BAD_REQUEST)






@api_view([ 'POST'])
@permission_classes([IsAuthenticated])
def create_standard_and_classrooms(request):

    if request.method == 'POST':
        # Step 1: Create Standard
        
        
        standard_serializer = StandardSerializer(data=request.data)

        if standard_serializer.is_valid():
            standard = standard_serializer.save(school=request.user)
            
            # Step 2: Create Classrooms
            number_of_divisions = int(request.data.get('number_of_divisions', 0))
            classrooms = []

            for i in range(number_of_divisions):

                division = chr(65 + i)  # A, B, C, ...
                classroom_data = {
                    'name': f'Division {division}',
                    'standard': standard.id,
                    'school': request.user.id,
                    'division': division,
                }
                
                classroom_serializer = ClassroomSerializer(data=classroom_data)
                if classroom_serializer.is_valid():
                    classroom = classroom_serializer.save(school=request.user)
                    classrooms.append(classroom_serializer.data)
                else:
                    # If any classroom creation fails, delete the standard and return error
                    standard.delete()
                    return Response(classroom_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # If all successful, return created data
            response_data = {
                'standard': standard_serializer.data,
                'classrooms': classrooms,
                'grade_id': str(standard.grade.id),  

            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(standard_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
@api_view(['DELETE','GET','PATCH'])
@permission_classes([IsAuthenticated])
def classroom_instance_manager(request,pk=None):
    if request.method=='GET' and pk is not None:
        
        classroom = Classroom.objects.filter(pk=pk).select_related(
            'standard', 'room'
        ).prefetch_related(
            Prefetch('class_subjects', queryset=ClassSubject.objects.all().prefetch_related(
                Prefetch('class_subject_subjects', queryset=ClassSubjectSubject.objects.all().select_related('subject').prefetch_related('assigned_teachers'))
            ))
        ).first()
        serializer = ClassroomDetailSerializer(classroom)
        return Response(serializer.data)


       
    elif request.method=="DELETE" and pk is not None:
        try:
            with transaction.atomic():
                classroom = Classroom.objects.select_for_update().get(id=pk)
                
                # Check if the user has permission to delete the classroom
                if classroom.school != request.user:
                    return Response(
                        {"error": 'You do not have permission to perform this action.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Perform any necessary cleanup or related object deletions here
                
                classroom.delete()
                
                return Response({"message": "Classroom deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        
        except Classroom.DoesNotExist:
            return Response({"error": "Classroom not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'PATCH' and pk is not None:

   
      
        try:
            classroom = Classroom.objects.get(pk=pk)
        except Classroom.DoesNotExist:
            return Response({"error": "Classroom not found"}, status=status.HTTP_404_NOT_FOUND)

        room_data = request.data.get('room')
        number_of_students = request.data.get('number_of_students')

        with transaction.atomic():
            try:
                if room_data:
                    current_room=classroom.room
                    room_name = f"room {classroom.standard.short_name} {classroom.name}"

                    if current_room:
                        current_room.occupied=False
                        current_room.name=f"{current_room.room_number} free room"
                        current_room.save()
                    if 'id' in room_data:  # Existing room
                        try:
                            room = Room.objects.get(pk=room_data['id'])
                            room_serializer = RoomSerializer(room, data={
                                'name': room_name,
                                'occupied': True,
                                'room_type':'CLASSROOM',
                                **room_data  # Include other fields from room_data
                            }, partial=True)
                            if room_serializer.is_valid():
                                room = room_serializer.save(school=request.user)
                            else:
                                return Response(room_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        except Room.DoesNotExist:
                            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)
                    else:  # New room
                        room_serializer = RoomSerializer(data={
                            'name': room_name,
                            'room_number': room_data.get('room_number', ''),
                            'capacity': room_data.get('capacity', 0),
                            'occupied': True
                        })
                        if room_serializer.is_valid():
                            room = room_serializer.save(school=request.user)
                        else:
                            return Response(room_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # Prepare data for classroom update
                classroom_update_data = {}
                if room_data:
                    classroom_update_data['room'] = room.id
                if number_of_students is not None:
                    classroom_update_data['number_of_students'] = number_of_students

                # Use ClassroomSerializer for updating the classroom
                classroom_serializer = ClassroomSerializer(classroom, data=classroom_update_data, partial=True)
                if classroom_serializer.is_valid():
                    updated_classroom = classroom_serializer.save()
                    return Response(ClassroomSerializer(updated_classroom).data)
                else:
                    return Response(classroom_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                # Log the exception here if needed
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
                



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def standard_instance_manager(request,pk):
    if request.method=='GET':
        
            pass
    elif request.method=="DELETE" and pk is not None:
        try:
            with transaction.atomic():
                standard = Standard.objects.select_for_update().get(id=pk)
                
                # Check if the user has permission to delete the classroom
                if standard.school != request.user:
                    return Response(
                        {"error": 'You do not have permission to perform this action.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Perform any necessary cleanup or related object deletions here
                
                standard.delete()
                
                return Response({"message": "Classroom deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        
        except Classroom.DoesNotExist:
            return Response({"error": "Classroom not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_subjects_with_available_teachers(request,pk):
    if pk is not None:
        try:
            grade=Grade.objects.get(id=pk)
        except Grade.DoesNotExist:
            return Response({"error": "Grade not found"}, status=404)
        subjects=Subject.objects.filter(
            school=request.user,  ).prefetch_related(
                Prefetch(
                    'qualified_teachers',
                    queryset=Teacher.objects.filter(grades=grade.id),
                    to_attr='available_teachers'
                )
            )
        subjects_with_teachers = [
        subject for subject in subjects if subject.available_teachers
    ]
        serializer = SubjectWithTeachersSerializer(subjects_with_teachers, many=True)
        return Response(serializer.data)


    


@api_view([ 'POST'])
@permission_classes([IsAuthenticated])
def assign_subjects_to_all_classrooms(request, pk):
    
    if pk is not None:
        try:
            standard = Standard.objects.get(id=pk)
        except Standard.DoesNotExist:
            return Response({"error": "Standard not found"}, status=status.HTTP_404_NOT_FOUND)

        # Step 1: Collect all classrooms from this standard using reverse relation
        classrooms = standard.classrooms.all()

    
        if request.method == 'POST':
            created_subjects = []
            
            # Wrap the entire creation process in a transaction
            with transaction.atomic():
                for classroom in classrooms:
                    classroom.class_subjects.all().delete()

                    for subject_data in request.data.get('selectedSubjects', []):
                        subject_data['class_room'] = classroom.id
                        subject_data['school'] = request.user.id

                        serializer = ClassSubjectSerializer(data=subject_data)
                        if serializer.is_valid():
                            serializer.save()
                            created_subjects.append(serializer.data)
                        else:
                            # If any serializer is invalid, raise an exception to rollback the transaction
                            raise serializers.ValidationError(serializer.errors)

            return Response(created_subjects, status=status.HTTP_201_CREATED)
    return Response({"error:primary key not be null"})

@api_view([ 'POST'])
@permission_classes([IsAuthenticated])
def assign_subjects_to_single_classroom(request, pk):
    
    if pk is not None:
        try:
            classroom = Classroom.objects.get(id=pk)
        except Classroom.DoesNotExist:
            return Response({"error": "Standard not found"}, status=status.HTTP_404_NOT_FOUND)


    
        if request.method == 'POST':
            created_subjects = []
            
            # Wrap the entire creation process in a transaction
            with transaction.atomic():
                

                    for subject_data in request.data.get('selectedSubjects', []):
                        subject_data['class_room'] = classroom.id
                        subject_data['school'] = request.user.id

                        serializer = ClassSubjectSerializer(data=subject_data)
                        if serializer.is_valid():
                            serializer.save()
                            created_subjects.append(serializer.data)
                        else:
                            # If any serializer is invalid, raise an exception to rollback the transaction
                            raise serializers.ValidationError(serializer.errors)

            return Response(created_subjects, status=status.HTTP_201_CREATED)
    return Response({"error:primary key not be null"})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_elective_group(request):
    logger.info(f"Received payload: {request.data}")
    serializer = ElectiveGroupCreateSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        logger.info(f"Validated data: {data}")
        
        try:
            standard = Standard.objects.get(id=data['standardId'])
        except Standard.DoesNotExist:
            return Response(
                {"error": f"Standard with id {data['standardId']} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get or create the ElectiveGroup
        elective_group, created = ElectiveGroup.objects.get_or_create(
            id=data.get('groupId'),  # Use the provided groupId if it exists
            defaults={
                'name': data['groupName'],
                'standard': standard,
                'school': request.user
            }
        )
        if not created:
            elective_group.name = data['groupName']
            elective_group.standard = standard
            elective_group.save()

        updated_subjects = []
        not_found_subjects = []

        # Update ClassSubjects and preferred rooms
        with transaction.atomic():
            for division_data in data['divisions']:
                try:
                    class_subject = ClassSubject.objects.get(
                        id=division_data['id'],
                        class_room_id=division_data['classroom_id'],
                        school=request.user
                    )
                    # Check if the elective_group is different before updating
                    if class_subject.elective_group != elective_group:
                        class_subject.elective_group = elective_group
                        class_subject.save()
                        updated_subjects.append(class_subject.id)
                except ClassSubject.DoesNotExist:
                    not_found_subjects.append(division_data['id'])

            # Update preferred rooms
            if 'preferredRooms' in data:
                preferred_room_ids = data['preferredRooms']
                logger.info(f"Preferred room IDs received: {preferred_room_ids}")
                
                preferred_rooms = Room.objects.filter(id__in=preferred_room_ids)
                logger.info(f"Found {preferred_rooms.count()} rooms")
                
                elective_group.preferred_rooms.set(preferred_rooms)
                logger.info(f"Rooms assigned to elective group: {[str(room.id) for room in elective_group.preferred_rooms.all()]}")

        # Prepare response data
        response_data = ElectiveGroupGetSerializer(elective_group).data
        response_data['updated_subjects'] = updated_subjects
        if not_found_subjects:
            response_data['not_found_subjects'] = not_found_subjects

        # Determine the appropriate status code
        if created:
            status_code = status.HTTP_201_CREATED
        elif updated_subjects or 'preferredRooms' in data:
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_304_NOT_MODIFIED

        logger.info(f"Final response data: {response_data}")
        return Response(response_data, status=status_code)
    
    logger.error(f"Serializer errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def elective_subject_add_view(request, pk):
    try:
        standard = Standard.objects.get(id=pk)
    except Standard.DoesNotExist:
        return Response({"error": "Standard not found"}, status=status.HTTP_404_NOT_FOUND)

    existing_elective_groups = standard.electives_groups.all()
    classrooms = standard.classrooms.all()

    data = {
        'existing_elective_groups': existing_elective_groups,
        'classrooms': classrooms
    }

    serializer = ElectiveSubjectAddSerializer(data)
    return Response(serializer.data)




@api_view(["GET", "DELETE", "PUT"])
@permission_classes([IsAuthenticated])
def classsubject_instance_manager(request, pk):
    if not pk:
        return Response({"error": "Primary key (pk) is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        class_subject = ClassSubject.objects.filter(school=request.user, id=pk).prefetch_related(
            Prefetch('class_subject_subjects', queryset=ClassSubjectSubject.objects.all().select_related('subject').prefetch_related('assigned_teachers'))
        ).first()
        
        if not class_subject:
            return Response({"error": "ClassSubject not found."}, status=status.HTTP_404_NOT_FOUND)

    except ObjectDoesNotExist:
        return Response({"error": "ClassSubject not found."}, status=status.HTTP_404_NOT_FOUND)
    except DatabaseError as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        serializer = ClassSubjectSerializer(class_subject)
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        try:
            class_subject.delete()
            return Response({"message": "ClassSubject deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except DatabaseError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'PUT':
        serializer = ClassSubjectSerializer(class_subject, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data)
            except DatabaseError as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
    return Response({"error": "Invalid request method."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)




@api_view(['PUT'])
def update_class_subject(request, pk):

    try:
        class_subject = ClassSubject.objects.get(pk=pk)
    except ClassSubject.DoesNotExist:
        return Response({"error": "ClassSubject not found"}, status=status.HTTP_404_NOT_FOUND)
    print(request.data)
    serializer = ClassSubjectUpdateSerializer(class_subject, data=request.data, partial=True)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




    






