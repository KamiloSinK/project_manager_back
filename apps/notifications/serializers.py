from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import Notification
from apps.authentication.serializers import UserSerializer

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    
    recipient = UserSerializer(read_only=True)
    sender = UserSerializer(read_only=True)
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'sender', 'type', 'priority', 'title',
            'message', 'is_read', 'read_at', 'related_project', 'related_task',
            'extra_data', 'created_at', 'updated_at', 'time_since'
        )
        read_only_fields = (
            'id', 'recipient', 'sender', 'created_at', 'updated_at'
        )
    

    
    def get_time_since(self, obj):
        """Get human-readable time since notification was created."""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for notification lists."""
    
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = (
            'id', 'sender_name', 'type', 'priority', 'title',
            'message', 'is_read', 'created_at', 'time_since'
        )
    

    
    def get_time_since(self, obj):
        """Get human-readable time since notification was created."""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications."""
    
    recipient_id = serializers.IntegerField(write_only=True)
    sender_id = serializers.IntegerField(write_only=True, required=False)
    related_project_id = serializers.IntegerField(write_only=True, required=False)
    related_task_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'recipient_id', 'sender_id', 'type', 'priority', 'title',
            'message', 'related_project_id', 'related_task_id', 'extra_data'
        )
        read_only_fields = ('id',)
    
    def validate_recipient_id(self, value):
        """Validate recipient exists and is active."""
        try:
            user = User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Usuario destinatario no encontrado o inactivo."
            )
        return value
    
    def validate_sender_id(self, value):
        """Validate sender exists and is active."""
        if value is not None:
            try:
                user = User.objects.get(id=value, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "Usuario remitente no encontrado o inactivo."
                )
        return value
    
    def validate_related_project_id(self, value):
        """Validate project exists."""
        if value is not None:
            from apps.projects.models import Project
            try:
                Project.objects.get(id=value)
            except Project.DoesNotExist:
                raise serializers.ValidationError(
                    "Proyecto no encontrado."
                )
        return value
    
    def validate_related_task_id(self, value):
        """Validate task exists."""
        if value is not None:
            from apps.tasks.models import Task
            try:
                Task.objects.get(id=value)
            except Task.DoesNotExist:
                raise serializers.ValidationError(
                    "Tarea no encontrada."
                )
        return value
    
    def validate(self, attrs):
        """Validate the notification data."""
        # Validate that required fields are present
        if not attrs.get('title'):
            raise serializers.ValidationError({
                'title': 'Este campo es requerido.'
            })
        
        if not attrs.get('message'):
            raise serializers.ValidationError({
                'message': 'Este campo es requerido.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create notification."""
        recipient_id = validated_data.pop('recipient_id')
        sender_id = validated_data.pop('sender_id', None)
        related_project_id = validated_data.pop('related_project_id', None)
        related_task_id = validated_data.pop('related_task_id', None)
        
        # Set recipient
        validated_data['recipient_id'] = recipient_id
        
        # Set sender if provided
        if sender_id:
            validated_data['sender_id'] = sender_id
        
        # Set related objects if provided
        if related_project_id:
            validated_data['related_project_id'] = related_project_id
        
        if related_task_id:
            validated_data['related_task_id'] = related_task_id
        
        return Notification.objects.create(**validated_data)


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notifications (mainly for marking as read)."""
    
    class Meta:
        model = Notification
        fields = ('is_read',)


class BulkNotificationUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating notifications."""
    
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Lista de IDs de notificaciones. Si no se proporciona, se actualizarán todas."
    )
    is_read = serializers.BooleanField(default=True)
    
    def validate_notification_ids(self, value):
        """Validate notification IDs exist and belong to the user."""
        if value:
            user = self.context['request'].user
            existing_ids = set(
                Notification.objects.filter(
                    id__in=value,
                    recipient=user
                ).values_list('id', flat=True)
            )
            
            invalid_ids = set(value) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(
                    f"Notificaciones no encontradas o sin acceso: {list(invalid_ids)}"
                )
        
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics."""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    read_notifications = serializers.IntegerField()
    notifications_today = serializers.IntegerField()
    notifications_this_week = serializers.IntegerField()
    recent_notifications = NotificationListSerializer(many=True)


class NotificationPreferencesSerializer(serializers.Serializer):
    """Serializer for notification preferences (future feature)."""
    
    email_notifications = serializers.BooleanField(default=True)
    push_notifications = serializers.BooleanField(default=True)
    project_updates = serializers.BooleanField(default=True)
    task_assignments = serializers.BooleanField(default=True)
    task_comments = serializers.BooleanField(default=True)
    project_invitations = serializers.BooleanField(default=True)
    deadline_reminders = serializers.BooleanField(default=True)
    
    def validate(self, attrs):
        """Validate notification preferences."""
        # At least one notification type should be enabled
        notification_types = [
            'project_updates', 'task_assignments', 'task_comments',
            'project_invitations', 'deadline_reminders'
        ]
        
        if not any(attrs.get(key, True) for key in notification_types):
            raise serializers.ValidationError(
                "Al menos un tipo de notificación debe estar habilitado."
            )
        
        return attrs