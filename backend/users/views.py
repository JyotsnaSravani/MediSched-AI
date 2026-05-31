"""
Views for authentication and user management.
Implements FR-UA-01 through FR-UA-06.
"""

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import UserSerializer, LoginSerializer, UserCreateSerializer
from .permissions import IsAdmin

User = get_user_model()


@extend_schema(
    request=LoginSerializer,
    responses={200: {
        'type': 'object',
        'properties': {
            'access': {'type': 'string'},
            'refresh': {'type': 'string'},
            'user': {'type': 'object'}
        }
    }},
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login endpoint - returns JWT access and refresh tokens.
    FR-UA-01: JWT authentication.
    
    POST /api/v1/auth/login/
    Body: {"email": "user@example.com", "password": "password"}
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Authenticate user
    user = authenticate(request, username=email, password=password)
    
    if user is None:
        return Response(
            {
                'error': 'INVALID_CREDENTIALS',
                'message': 'Invalid email or password',
                'status_code': 401
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {
                'error': 'ACCOUNT_DISABLED',
                'message': 'This account has been disabled',
                'status_code': 403
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    })


@extend_schema(
    request={'type': 'object', 'properties': {'refresh': {'type': 'string'}}},
    responses={200: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}},
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint - blacklists the refresh token.
    
    POST /api/v1/auth/logout/
    Body: {"refresh": "refresh_token"}
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {
                'error': 'LOGOUT_FAILED',
                'message': str(e),
                'status_code': 400
            },
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(tags=['Authentication'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user details.
    
    GET /api/v1/auth/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserListCreateView(generics.ListCreateAPIView):
    """
    List all users or create a new user.
    Only Admin can access.
    
    GET /api/v1/auth/users/
    POST /api/v1/auth/users/
    """
    queryset = User.objects.all()
    permission_classes = [IsAdmin]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a user.
    Only Admin can access.
    
    GET /api/v1/auth/users/{id}/
    PUT /api/v1/auth/users/{id}/
    DELETE /api/v1/auth/users/{id}/
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
