from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with role-based access control."""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        COLLABORATOR = 'collaborator', 'Colaborador'
        VIEWER = 'viewer', 'Visor'
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text='Rol del usuario en el sistema'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    def is_collaborator(self):
        return self.role == self.Role.COLLABORATOR
    
    def is_viewer(self):
        return self.role == self.Role.VIEWER
    
    def can_manage_projects(self):
        return self.role in [self.Role.ADMIN, self.Role.COLLABORATOR]
    
    def can_manage_tasks(self):
        return self.role in [self.Role.ADMIN, self.Role.COLLABORATOR]
