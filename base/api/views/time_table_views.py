from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view,permission_classes
from ...optapy_solver.main import run_optimization

@api_view(['GET'])
@permission_classes([IsAuthenticated])

def run_module_view(request):
    result = run_optimization()
    print("result got")
    return Response({"message": str(result)}, status=status.HTTP_200_OK)