from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    RegisterView,
    LogoutView,
    UserProfileView,
    ChangePasswordView,
    PasswordResetView,
    PasswordResetConfirmView,
    UserListView,
    user_permissions,
    user_stats,
    AdminUserListView,
    AdminUserUpdateView,
)

app_name = 'authentication'

urlpatterns = [
    # Endpoints de autenticación
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Endpoints de perfil de usuario
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Endpoints de recuperación de contraseña
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path(
        'password-reset-confirm/<str:uidb64>/<str:token>/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),
    
    # Endpoints de gestión de usuarios
    path('users/', UserListView.as_view(), name='user_list'),
    path('permissions/', user_permissions, name='user_permissions'),
    path('stats/', user_stats, name='user_stats'),
    
    # Endpoints de administración (solo admin)
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:id>/', AdminUserUpdateView.as_view(), name='admin_user_update'),
]