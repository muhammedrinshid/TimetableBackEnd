from rest_framework import status
from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..serializer.user_serializer import UserSerializer,LevelSerializer,SubjectSerializer,UserConstraintSettingsSerializer
from django.shortcuts import get_object_or_404
from ...models import User,Level,Subject,UserConstraintSettings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = get_object_or_404(User, id=request.user.id)
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile_image(request):
    user = request.user
    
    if 'profile_image' in request.FILES:
        user.profile_image = request.FILES['profile_image']
        user.save()
        return Response({'message': 'Profile image updated successfully'}, status=status.HTTP_200_OK)
    elif request.data.get('profile_image') is None:
        # Remove the image if null is sent
        if user.profile_image:
            user.profile_image.delete(save=False)
            user.profile_image = None
            user.save()
        return Response({'message': 'Profile image removed successfully'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticated])
@api_view(["PUT",'POST','GET','DELETE'])
def level_create_update(request,pk=None):
    
 
    if request.method =="POST":
        serializer=LevelSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(school=request.user)
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'PUT' and pk is not None:
        
        try:
           
            level=Level.objects.get(id=pk)
        except Level.DoesNotExist:
            return Response (status=status.HTTP_404_NOT_FOUND)
        
            
        
        # Check ownership
        if level.school != request.user: 
            return Response({'error': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer=LevelSerializer(level,data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)     
    elif request.method =='DELETE' and pk is not None:
        try:
            level =Level.objects.get(id=pk)
        except Level.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if level.school!=request.user:
            return Response({'error': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        level.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
               
@permission_classes([IsAuthenticated])
@api_view(["GET"])
def levels(request):
    """
    API view to retrieve a list of all levels associated with the authenticated user.
    """
    try:
        user = request.user
        levels = Level.objects.filter(school=user)
        serializer = LevelSerializer(levels, many=True)
        
        if not levels.exists():
            return Response({"detail": "No levels found for the current user."}, status=status.HTTP_200_OK)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
    
    
    
@permission_classes([IsAuthenticated])
@api_view(["GET"])
def subjects(request):
    """
    API view to retrieve a list of all subjects associated with the authenticated user.
    """
    try:
        user = request.user
        subjects = Subject.objects.filter(school=user)
        serializer = SubjectSerializer(subjects, many=True)
        
        

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    





@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_constraint_settings(request):
    try:
        constraint_settings = UserConstraintSettings.objects.get(user=request.user)
    except UserConstraintSettings.DoesNotExist:
        constraint_settings = UserConstraintSettings(user=request.user)
        constraint_settings.save()

    if request.method == 'GET':
        serializer = UserConstraintSettingsSerializer(constraint_settings)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserConstraintSettingsSerializer(constraint_settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
