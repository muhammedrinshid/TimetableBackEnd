from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ...models import Teacher
from ..serializer.teacher_serializer import TeacherSerializer
from django.db.models import Count

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher(request,pk=None):
    if request.method == 'POST':
        print("POST data:", request.POST)
        print("FILES:", request.FILES)
        serializer = TeacherSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            teacher = serializer.save(school=request.user)
            if 'profile_image' in request.FILES:
                teacher.profile_image = request.FILES['profile_image']
                teacher.save()
            return Response(TeacherSerializer(teacher).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        teachers = Teacher.objects.filter(school=request.user)
        serializer = TeacherSerializer(teachers, many=True)
        return Response(serializer.data)

    elif request.method == 'PUT' and pk is not None:
        try:
            teacher = Teacher.objects.get(id=pk, school=request.user)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TeacherSerializer(teacher, data=request.data, partial=True)
        if serializer.is_valid():
            teacher = serializer.save()
            if 'profile_image' in request.FILES:
                teacher.profile_image = request.FILES['profile_image']
                teacher.save()
            return Response(TeacherSerializer(teacher).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        try:
            teacher = Teacher.objects.get(id=pk, school=request.user)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

        teacher.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subject_teacher_count(request):
    school=request.user
    subject_data=school.subjects.annotate(count=Count('qualified_teachers')).values('name','count')
    formated_data=[
        {
            "subject":item["name"],
            "count":item["count"]
        }
            for item in subject_data
 
    ]
    
    return Response({'subjectData': formated_data})



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teachers(request):
    try:
        user = request.user
        teachers = Teacher.objects.filter(school=user)
        serializer = TeacherSerializer(teachers, many=True)
        
        if not teachers.exists():
            return Response([], status=status.HTTP_200_OK)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
    