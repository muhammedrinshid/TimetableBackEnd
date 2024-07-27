






from rest_framework import status,serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ...models import Standard, Classroom, Grade,Subject,Teacher,ClassSubject,ClassSubjectSubject
from rest_framework.decorators import api_view,permission_classes
from ..serializer.class_room_serializer import StandardSerializer, ClassroomSerializer,GradeLightSerializer,SubjectWithTeachersSerializer,ClassSubjectSerializer,ClassroomDetailSerializer
from django.db import transaction
from django.db.models import Prefetch


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
    
    print(request.data)
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
                print(request.data)

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
    
    
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def classroom_instance_manager(request,pk=None):
    if request.method=='GET' and pk is not None:
        
        classroom = Classroom.objects.filter(pk=pk).select_related(
            'standard', 'room'
        ).prefetch_related(
            Prefetch('class_subjects', queryset=ClassSubject.objects.all().prefetch_related(
                Prefetch('class_subjects', queryset=ClassSubjectSubject.objects.all().select_related('subject').prefetch_related('assigned_teachers'))
            ))
        ).first()
        serializer = ClassroomDetailSerializer(classroom)
        return Response(serializer.data)


        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
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