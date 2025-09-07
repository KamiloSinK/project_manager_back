from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from drf_spectacular.utils import extend_schema

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer
)

User = get_user_model()


@extend_schema(tags=['Autenticación y Usuarios'], summary='Obtener tokens JWT')
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para obtener tokens JWT.
    
    Permite a los usuarios autenticarse y obtener tokens de acceso y refresh.
    """
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=['Autenticación y Usuarios'], summary='Renovar token JWT')
class CustomTokenRefreshView(TokenRefreshView):
    """
    Vista personalizada para renovar tokens JWT.
    
    Permite renovar el token de acceso usando el token de refresh.
    """
    pass


@extend_schema(tags=['Autenticación y Usuarios'], summary='Registrar nuevo usuario')
class RegisterView(generics.CreateAPIView):
    """
    Vista de registro de usuarios.
    
    Permite crear nuevas cuentas de usuario y devuelve tokens JWT automáticamente.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Create user and return tokens."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Usuario registrado exitosamente.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Autenticación y Usuarios'], summary='Cerrar sesión')
class LogoutView(APIView):
    """
    Vista para cerrar sesión de usuario.
    
    Permite cerrar la sesión del usuario invalidando el token de refresh.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Logout user by blacklisting refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Sesión cerrada exitosamente.'
            }, status=status.HTTP_200_OK)
        
        except (InvalidToken, TokenError):
            return Response({
                'error': 'Token inválido.'
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Autenticación y Usuarios'], summary='Perfil de usuario')
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Vista del perfil de usuario.
    
    Permite obtener y actualizar la información del perfil del usuario autenticado.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Return current user."""
        return self.request.user
    
    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer


@extend_schema(tags=['Autenticación y Usuarios'], summary='Cambiar contraseña')
class ChangePasswordView(APIView):
    """
    Vista para cambiar contraseña de usuario.
    
    Permite al usuario autenticado cambiar su contraseña actual por una nueva.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Change user password."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Contraseña cambiada exitosamente.'
            }, status=status.HTTP_200_OK)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(tags=['Autenticación y Usuarios'], summary='Solicitar restablecimiento de contraseña')
class PasswordResetView(APIView):
    """
    Vista para solicitar restablecimiento de contraseña.
    
    Envía un email con instrucciones para restablecer la contraseña del usuario.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Send password reset email."""
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email, is_active=True)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset URL (you'll need to implement the frontend route)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            
            # Send email
            subject = 'Restablecer contraseña - Project Manager'
            message = render_to_string('authentication/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Project Manager'
            })
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=message,
                    fail_silently=False,
                )
                
                return Response({
                    'message': 'Se ha enviado un email con instrucciones para restablecer tu contraseña.'
                }, status=status.HTTP_200_OK)
            
            except Exception as e:
                return Response({
                    'error': 'Error al enviar el email. Inténtalo más tarde.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(tags=['Autenticación y Usuarios'], summary='Confirmar restablecimiento de contraseña')
class PasswordResetConfirmView(APIView):
    """
    Vista para confirmar restablecimiento de contraseña.
    
    Permite establecer una nueva contraseña usando el token de restablecimiento.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, uidb64, token):
        """Confirm password reset."""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Token inválido.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not default_token_generator.check_token(user, token):
            return Response({
                'error': 'Token inválido o expirado.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                'message': 'Contraseña restablecida exitosamente.'
            }, status=status.HTTP_200_OK)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(tags=['Autenticación y Usuarios'], summary='Listar usuarios')
class UserListView(generics.ListAPIView):
    """
    Vista para listar usuarios.
    
    Los administradores pueden ver todos los usuarios.
    Los colaboradores pueden ver usuarios de sus proyectos.
    Los visualizadores solo pueden verse a sí mismos.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return users based on current user role."""
        user = self.request.user
        
        if user.is_admin:
            # Admins can see all users
            return User.objects.all().order_by('first_name', 'last_name')
        elif user.is_collaborator:
            # Collaborators can see users in their projects
            return User.objects.filter(
                project_assignments__project__assignments__user=user
            ).distinct().order_by('first_name', 'last_name')
        else:
            # Viewers can only see themselves
            return User.objects.filter(id=user.id)


@extend_schema(tags=['Autenticación y Usuarios'], summary='Obtener permisos del usuario')
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_permissions(request):
    """Get current user permissions."""
    user = request.user
    
    permissions_data = {
        'can_manage_projects': user.can_manage_projects(),
        'can_manage_tasks': user.can_manage_tasks(),
        'is_admin': user.is_admin,
        'is_collaborator': user.is_collaborator,
        'is_viewer': user.is_viewer,
        'role': user.role,
    }
    
    return Response(permissions_data)


@extend_schema(tags=['Autenticación y Usuarios'], summary='Obtener estadísticas del usuario')
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get current user statistics."""
    user = request.user
    
    # Import here to avoid circular imports
    from apps.projects.models import Project, ProjectAssignment
    from apps.tasks.models import Task
    
    stats = {
        'total_projects': 0,
        'active_projects': 0,
        'total_tasks': 0,
        'pending_tasks': 0,
        'completed_tasks': 0,
    }
    
    if user.is_admin:
        # Admins see all stats
        stats['total_projects'] = Project.objects.count()
        stats['active_projects'] = Project.objects.filter(status='active').count()
        stats['total_tasks'] = Task.objects.count()
        stats['pending_tasks'] = Task.objects.filter(status='pending').count()
        stats['completed_tasks'] = Task.objects.filter(status='completed').count()
    else:
        # Other users see only their stats
        user_projects = Project.objects.filter(assignments__user=user)
        stats['total_projects'] = user_projects.count()
        stats['active_projects'] = user_projects.filter(status='active').count()
        
        user_tasks = Task.objects.filter(assigned_to=user)
        stats['total_tasks'] = user_tasks.count()
        stats['pending_tasks'] = user_tasks.filter(status='pending').count()
        stats['completed_tasks'] = user_tasks.filter(status='completed').count()
    
    return Response(stats)
