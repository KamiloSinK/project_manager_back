from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from apps.projects.models import ProjectAssignment
from apps.tasks.models import Task, TaskComment
from .models import Notification

User = get_user_model()


@receiver(post_save, sender=ProjectAssignment)
def create_project_assignment_notification(sender, instance, created, **kwargs):
    """
    Crear notificación cuando un usuario es asignado a un proyecto.
    """
    if created:
        try:
            Notification.create_project_assigned_notification(instance)
        except Exception as e:
            # Log error but don't fail the assignment
            print(f"Error creating project assignment notification: {e}")


@receiver(post_save, sender=Task)
def create_task_notification(sender, instance, created, **kwargs):
    """
    Crear notificación cuando se crea una nueva tarea.
    """
    if created and instance.assigned_to:
        try:
            # Obtener quien creó la tarea (puede ser el usuario actual o el creador del proyecto)
            assigned_by = getattr(instance, '_assigned_by', instance.created_by)
            Notification.create_task_assigned_notification(instance, assigned_by)
        except Exception as e:
            # Log error but don't fail the task creation
            print(f"Error creating task assignment notification: {e}")


@receiver(post_save, sender=TaskComment)
def create_comment_notification(sender, instance, created, **kwargs):
    """
    Crear notificación cuando se agrega un comentario a una tarea.
    """
    if created:
        try:
            Notification.create_comment_notification(instance)
        except Exception as e:
            # Log error but don't fail the comment creation
            print(f"Error creating comment notification: {e}")