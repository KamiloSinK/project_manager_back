from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Project(models.Model):
    """Model for managing projects."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        IN_PROGRESS = 'in_progress', 'En Progreso'
        COMPLETED = 'completed', 'Completado'
        CANCELLED = 'cancelled', 'Cancelado'
    
    name = models.CharField(
        max_length=200,
        help_text='Nombre del proyecto'
    )
    description = models.TextField(
        blank=True,
        help_text='Descripción detallada del proyecto'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text='Estado actual del proyecto'
    )
    start_date = models.DateField(
        help_text='Fecha de inicio del proyecto'
    )
    end_date = models.DateField(
        help_text='Fecha de finalización del proyecto'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_projects',
        help_text='Usuario que creó el proyecto'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects_project'
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': 'La fecha de finalización debe ser posterior a la fecha de inicio.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if project is currently active."""
        return self.status in [self.Status.PENDING, self.Status.IN_PROGRESS]
    
    @property
    def is_overdue(self):
        """Check if project is overdue."""
        if self.status == self.Status.COMPLETED:
            return False
        return timezone.now().date() > self.end_date
    
    @property
    def duration_days(self):
        """Calculate project duration in days."""
        return (self.end_date - self.start_date).days
    
    @property
    def days_remaining(self):
        """Calculate days remaining until project end date."""
        if self.status == self.Status.COMPLETED:
            return 0
        today = timezone.now().date()
        if today > self.end_date:
            return 0  # Project is overdue
        return (self.end_date - today).days
    
    def get_assigned_users(self):
        """Get all users assigned to this project."""
        return self.assignments.select_related('user').all()
    
    def get_tasks_count(self):
        """Get total number of tasks in this project."""
        return self.tasks.count()
    
    def get_completed_tasks_count(self):
        """Get number of completed tasks in this project."""
        return self.tasks.filter(status='completed').count()
    
    def get_progress_percentage(self):
        """Calculate project progress based on completed tasks."""
        total_tasks = self.get_tasks_count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.get_completed_tasks_count()
        return round((completed_tasks / total_tasks) * 100, 2)


class ProjectAssignment(models.Model):
    """Model for assigning users to projects."""
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text='Proyecto asignado'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_assignments',
        help_text='Usuario asignado'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_projects',
        help_text='Usuario que realizó la asignación'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'projects_assignment'
        verbose_name = 'Asignación de Proyecto'
        verbose_name_plural = 'Asignaciones de Proyectos'
        unique_together = ['project', 'user']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.project.name}"
