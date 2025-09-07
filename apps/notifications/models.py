from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Model for managing user notifications."""
    
    class Type(models.TextChoices):
        TASK_ASSIGNED = 'task_assigned', 'Tarea Asignada'
        TASK_COMPLETED = 'task_completed', 'Tarea Completada'
        TASK_OVERDUE = 'task_overdue', 'Tarea Vencida'
        PROJECT_ASSIGNED = 'project_assigned', 'Proyecto Asignado'
        PROJECT_COMPLETED = 'project_completed', 'Proyecto Completado'
        COMMENT_ADDED = 'comment_added', 'Comentario Agregado'
        DEADLINE_REMINDER = 'deadline_reminder', 'Recordatorio de Fecha Límite'
        GENERAL = 'general', 'General'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Baja'
        MEDIUM = 'medium', 'Media'
        HIGH = 'high', 'Alta'
        URGENT = 'urgent', 'Urgente'
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='Usuario que recibe la notificación'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        help_text='Usuario que envía la notificación (opcional)'
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.GENERAL,
        help_text='Tipo de notificación'
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text='Prioridad de la notificación'
    )
    title = models.CharField(
        max_length=200,
        help_text='Título de la notificación'
    )
    message = models.TextField(
        help_text='Mensaje de la notificación'
    )
    is_read = models.BooleanField(
        default=False,
        help_text='Indica si la notificación ha sido leída'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora en que se leyó la notificación'
    )
    
    # Related objects (optional)
    related_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Proyecto relacionado (opcional)'
    )
    related_task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Tarea relacionada (opcional)'
    )
    
    # Additional data as JSON
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Datos adicionales en formato JSON'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications_notification'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.full_name}"
    
    def save(self, *args, **kwargs):
        # Set read_at when is_read changes to True
        if self.is_read and not self.read_at:
            self.read_at = timezone.now()
        elif not self.is_read:
            self.read_at = None
        
        super().save(*args, **kwargs)
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def is_urgent(self):
        """Check if notification is urgent."""
        return self.priority == self.Priority.URGENT
    
    @property
    def age_in_hours(self):
        """Calculate notification age in hours."""
        delta = timezone.now() - self.created_at
        return delta.total_seconds() / 3600
    
    @classmethod
    def create_task_assigned_notification(cls, task, assigned_by):
        """Create notification for task assignment."""
        return cls.objects.create(
            recipient=task.assigned_to,
            sender=assigned_by,
            type=cls.Type.TASK_ASSIGNED,
            priority=cls.Priority.MEDIUM,
            title=f'Nueva tarea asignada: {task.name}',
            message=f'Se te ha asignado la tarea "{task.name}" en el proyecto "{task.project.name}". Fecha de vencimiento: {task.due_date.strftime("%d/%m/%Y %H:%M")}',
            related_project=task.project,
            related_task=task,
            extra_data={
                'task_id': task.id,
                'project_id': task.project.id,
                'assigned_by_id': assigned_by.id
            }
        )
    
    @classmethod
    def create_task_completed_notification(cls, task, completed_by):
        """Create notification for task completion."""
        # Notify project creator and other assigned users
        recipients = [task.project.created_by]
        if task.created_by != task.project.created_by:
            recipients.append(task.created_by)
        
        notifications = []
        for recipient in recipients:
            if recipient != completed_by:  # Don't notify the person who completed it
                notification = cls.objects.create(
                    recipient=recipient,
                    sender=completed_by,
                    type=cls.Type.TASK_COMPLETED,
                    priority=cls.Priority.LOW,
                    title=f'Tarea completada: {task.name}',
                    message=f'{completed_by.full_name} ha completado la tarea "{task.name}" en el proyecto "{task.project.name}".',
                    related_project=task.project,
                    related_task=task,
                    extra_data={
                        'task_id': task.id,
                        'project_id': task.project.id,
                        'completed_by_id': completed_by.id
                    }
                )
                notifications.append(notification)
        
        return notifications
    
    @classmethod
    def create_project_assigned_notification(cls, project_assignment):
        """Create notification for project assignment."""
        return cls.objects.create(
            recipient=project_assignment.user,
            sender=project_assignment.assigned_by,
            type=cls.Type.PROJECT_ASSIGNED,
            priority=cls.Priority.MEDIUM,
            title=f'Asignado a proyecto: {project_assignment.project.name}',
            message=f'Has sido asignado al proyecto "{project_assignment.project.name}". Fecha de inicio: {project_assignment.project.start_date.strftime("%d/%m/%Y")}',
            related_project=project_assignment.project,
            extra_data={
                'project_id': project_assignment.project.id,
                'assigned_by_id': project_assignment.assigned_by.id
            }
        )
    
    @classmethod
    def create_comment_notification(cls, comment):
        """Create notification for new comment."""
        # Notify task assignee and creator (if different from comment author)
        recipients = []
        if comment.task.assigned_to and comment.task.assigned_to != comment.author:
            recipients.append(comment.task.assigned_to)
        if comment.task.created_by != comment.author and comment.task.created_by not in recipients:
            recipients.append(comment.task.created_by)
        
        notifications = []
        for recipient in recipients:
            notification = cls.objects.create(
                recipient=recipient,
                sender=comment.author,
                type=cls.Type.COMMENT_ADDED,
                priority=cls.Priority.LOW,
                title=f'Nuevo comentario en: {comment.task.name}',
                message=f'{comment.author.full_name} ha agregado un comentario en la tarea "{comment.task.name}".',
                related_project=comment.task.project,
                related_task=comment.task,
                extra_data={
                    'task_id': comment.task.id,
                    'project_id': comment.task.project.id,
                    'comment_id': comment.id,
                    'author_id': comment.author.id
                }
            )
            notifications.append(notification)
        
        return notifications
    
    @classmethod
    def get_unread_count_for_user(cls, user):
        """Get count of unread notifications for a user."""
        return cls.objects.filter(recipient=user, is_read=False).count()
    
    @classmethod
    def mark_all_as_read_for_user(cls, user):
        """Mark all notifications as read for a user."""
        return cls.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
