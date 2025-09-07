from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Task(models.Model):
    """Model for managing tasks within projects."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        IN_PROGRESS = 'in_progress', 'En Progreso'
        COMPLETED = 'completed', 'Completado'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Baja'
        MEDIUM = 'medium', 'Media'
        HIGH = 'high', 'Alta'
        URGENT = 'urgent', 'Urgente'
    
    name = models.CharField(
        max_length=200,
        help_text='Nombre de la tarea'
    )
    description = models.TextField(
        blank=True,
        help_text='Descripción detallada de la tarea'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text='Estado actual de la tarea'
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text='Prioridad de la tarea'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text='Proyecto al que pertenece la tarea'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text='Usuario asignado a la tarea'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        help_text='Usuario que creó la tarea'
    )
    due_date = models.DateTimeField(
        help_text='Fecha y hora de vencimiento de la tarea'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de finalización de la tarea'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks_task'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['due_date']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['project']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"
    
    def clean(self):
        """Validate task data."""
        if self.due_date:
            # Check if due date is not in the past
            if self.due_date.date() < timezone.now().date():
                raise ValidationError({
                    'due_date': 'La fecha de vencimiento no puede ser anterior a la fecha actual.'
                })
            
            # Check if due date is within project timeline
            if self.project:
                if self.due_date.date() < self.project.start_date:
                    raise ValidationError({
                        'due_date': 'La fecha de vencimiento no puede ser anterior al inicio del proyecto.'
                    })
                if self.due_date.date() > self.project.end_date:
                    raise ValidationError({
                        'due_date': 'La fecha de vencimiento no puede ser posterior al fin del proyecto.'
                    })
        
        # Validate assigned user is part of the project
        if self.assigned_to and self.project:
            if not self.project.assignments.filter(user=self.assigned_to).exists():
                raise ValidationError({
                    'assigned_to': 'El usuario asignado debe estar asignado al proyecto.'
                })
    
    def save(self, *args, **kwargs):
        # Set completed_at when status changes to completed
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != self.Status.COMPLETED:
            self.completed_at = None
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.status == self.Status.COMPLETED:
            return False
        return timezone.now() > self.due_date
    
    @property
    def days_until_due(self):
        """Calculate days until due date."""
        if self.status == self.Status.COMPLETED:
            return None
        delta = self.due_date.date() - timezone.now().date()
        return delta.days
    
    @property
    def is_urgent(self):
        """Check if task is urgent (due within 24 hours)."""
        if self.status == self.Status.COMPLETED:
            return False
        return self.due_date <= timezone.now() + timezone.timedelta(hours=24)
    
    def get_comments_count(self):
        """Get total number of comments for this task."""
        return self.comments.count()
    
    def can_be_edited_by(self, user):
        """Check if user can edit this task."""
        return (
            user.is_admin or
            user == self.created_by or
            user == self.assigned_to or
            self.project.assignments.filter(user=user).exists()
        )
    
    def can_be_deleted_by(self, user):
        """Check if user can delete this task."""
        return user.is_admin or user == self.created_by


class TaskComment(models.Model):
    """Model for comments on tasks."""
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text='Tarea comentada'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_comments',
        help_text='Autor del comentario'
    )
    content = models.TextField(
        help_text='Contenido del comentario'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks_comment'
        verbose_name = 'Comentario de Tarea'
        verbose_name_plural = 'Comentarios de Tareas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"Comentario de {self.author.full_name} en {self.task.name}"
    
    def clean(self):
        """Validate that author is assigned to the task or project."""
        if self.author and self.task:
            # Check if author is assigned to the task or project
            is_assigned_to_task = self.task.assigned_to == self.author
            is_assigned_to_project = self.task.project.assignments.filter(user=self.author).exists()
            is_task_creator = self.task.created_by == self.author
            
            if not (is_assigned_to_task or is_assigned_to_project or is_task_creator or self.author.is_admin):
                raise ValidationError({
                    'author': 'Solo los usuarios asignados a la tarea o proyecto pueden comentar.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def can_be_edited_by(self, user):
        """Check if user can edit this comment."""
        return user.is_admin or user == self.author
    
    def can_be_deleted_by(self, user):
        """Check if user can delete this comment."""
        return user.is_admin or user == self.author
