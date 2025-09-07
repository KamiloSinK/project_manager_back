from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

from .models import Task, TaskComment
from apps.authentication.serializers import UserSerializer
from apps.projects.models import Project

User = get_user_model()


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for task comments."""
    
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TaskComment
        fields = (
            'id', 'content', 'author', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')
    
    def validate_content(self, value):
        """Validate comment content."""
        if not value.strip():
            raise serializers.ValidationError(
                "El comentario no puede estar vacío."
            )
        return value.strip()


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for tasks."""
    
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = (
            'id', 'name', 'description', 'status', 'priority',
            'project', 'project_name', 'created_by', 'assigned_to',
            'assigned_to_id', 'due_date', 'created_at', 'updated_at',
            'comments', 'comments_count', 'is_overdue', 'days_remaining'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')
    
    def get_comments_count(self, obj):
        """Get total number of comments for this task."""
        return obj.comments.count()
    
    def validate_assigned_to_id(self, value):
        """Validate assigned user exists and is active."""
        if value is not None:
            try:
                user = User.objects.get(id=value, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "Usuario no encontrado o inactivo."
                )
        return value
    
    def validate_project(self, value):
        """Validate project exists and user has access."""
        user = self.context['request'].user
        
        # Check if user has access to the project
        if not user.is_superuser:
            if not value.assignments.filter(user=user).exists():
                raise serializers.ValidationError(
                    "No tienes acceso a este proyecto."
                )
        
        return value
    
    def validate(self, attrs):
        """Validate task data."""
        due_date = attrs.get('due_date')
        project = attrs.get('project') or (self.instance.project if self.instance else None)
        assigned_to_id = attrs.get('assigned_to_id')
        
        # Validate due date
        if due_date:
            # Check if due date is not in the past
            if due_date < date.today():
                raise serializers.ValidationError({
                    'due_date': 'La fecha de vencimiento no puede ser anterior a la fecha actual.'
                })
            
            # Check if due date is within project timeline
            if project:
                if due_date < project.start_date:
                    raise serializers.ValidationError({
                        'due_date': 'La fecha de vencimiento no puede ser anterior al inicio del proyecto.'
                    })
                if due_date > project.end_date:
                    raise serializers.ValidationError({
                        'due_date': 'La fecha de vencimiento no puede ser posterior al fin del proyecto.'
                    })
        
        # Validate assigned user has access to project
        if assigned_to_id and project:
            if not project.assignments.filter(user_id=assigned_to_id).exists():
                raise serializers.ValidationError({
                    'assigned_to_id': 'El usuario asignado debe tener acceso al proyecto.'
                })
        
        return attrs


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks."""
    
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = (
            'id', 'name', 'description', 'status', 'priority',
            'project', 'assigned_to_id', 'due_date'
        )
        read_only_fields = ('id',)
    
    def validate_assigned_to_id(self, value):
        """Validate assigned user exists and is active."""
        if value is not None:
            try:
                user = User.objects.get(id=value, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "Usuario no encontrado o inactivo."
                )
        return value
    
    def validate_project(self, value):
        """Validate project exists and user has access."""
        user = self.context['request'].user
        
        # Check if user has access to the project
        if not user.is_superuser:
            if not value.assignments.filter(user=user).exists():
                raise serializers.ValidationError(
                    "No tienes acceso a este proyecto."
                )
        
        return value
    
    def validate(self, attrs):
        """Validate task creation data."""
        due_date = attrs.get('due_date')
        project = attrs.get('project')
        assigned_to_id = attrs.get('assigned_to_id')
        
        # Validate due date
        if due_date:
            # Convert datetime to date for comparison if needed
            due_date_only = due_date.date() if hasattr(due_date, 'date') else due_date
            if due_date_only < date.today():
                raise serializers.ValidationError({
                    'due_date': 'La fecha de vencimiento no puede ser anterior a hoy.'
                })
        
        # Validate assigned user has access to project
        if assigned_to_id and project:
            if not project.assignments.filter(user_id=assigned_to_id).exists():
                raise serializers.ValidationError({
                    'assigned_to_id': 'El usuario asignado debe tener acceso al proyecto.'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create task with assigned user."""
        assigned_to_id = validated_data.pop('assigned_to_id', None)
        
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        
        # Set assigned_to if provided
        if assigned_to_id:
            validated_data['assigned_to_id'] = assigned_to_id
        
        task = Task.objects.create(**validated_data)
        return task


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tasks."""
    
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = (
            'name', 'description', 'status', 'priority',
            'assigned_to_id', 'due_date'
        )
    
    def validate_assigned_to_id(self, value):
        """Validate assigned user exists and is active."""
        if value is not None:
            try:
                user = User.objects.get(id=value, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "Usuario no encontrado o inactivo."
                )
        return value
    
    def validate(self, attrs):
        """Validate task update data."""
        assigned_to_id = attrs.get('assigned_to_id')
        
        # Validate assigned user has access to project
        if assigned_to_id and self.instance.project:
            if not self.instance.project.assignments.filter(user_id=assigned_to_id).exists():
                raise serializers.ValidationError({
                    'assigned_to_id': 'El usuario asignado debe tener acceso al proyecto.'
                })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update task with assigned user."""
        assigned_to_id = validated_data.pop('assigned_to_id', None)
        
        # Update assigned_to if provided
        if 'assigned_to_id' in self.initial_data:
            instance.assigned_to_id = assigned_to_id
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class TaskListSerializer(serializers.ModelSerializer):
    """Simplified serializer for task lists."""
    
    created_by = serializers.StringRelatedField()
    assigned_to = serializers.StringRelatedField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    comments_count = serializers.SerializerMethodField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = (
            'id', 'name', 'description', 'status', 'priority',
            'project', 'project_name', 'created_by', 'assigned_to',
            'due_date', 'created_at', 'comments_count',
            'is_overdue', 'days_remaining'
        )
    
    def get_comments_count(self, obj):
        """Get total number of comments for this task."""
        return obj.comments.count()


class TaskStatsSerializer(serializers.Serializer):
    """Serializer for task statistics."""
    
    total_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    in_progress_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    tasks_by_status = serializers.DictField()
    tasks_by_priority = serializers.DictField()
    my_tasks = TaskListSerializer(many=True)
    recent_tasks = TaskListSerializer(many=True)


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments."""
    
    class Meta:
        model = TaskComment
        fields = ('content',)
    
    def validate_content(self, value):
        """Validate comment content."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "El comentario no puede estar vacío."
            )
        
        # Validate content length
        if len(value.strip()) > 1000:
            raise serializers.ValidationError(
                "El comentario no puede exceder 1000 caracteres."
            )
        
        # Validate content is not just whitespace or special characters
        if not any(c.isalnum() for c in value):
            raise serializers.ValidationError(
                "El comentario debe contener al menos un carácter alfanumérico."
            )
        
        return value.strip()
    
    def validate(self, attrs):
        """Validate comment creation permissions."""
        task = self.context.get('task')
        user = self.context.get('request').user
        
        if not task:
            raise serializers.ValidationError(
                "Tarea no especificada para el comentario."
            )
        
        # Check if user has permission to comment on this task
        if not user.is_superuser:
            # User must be assigned to the project
            has_project_access = task.project.assignments.filter(user=user).exists()
            
            if not has_project_access:
                raise serializers.ValidationError(
                    "No tienes permisos para comentar en esta tarea."
                )
            
            # Additional check: user should be either assigned to task, creator, or project manager
            is_task_participant = (
                task.assigned_to == user or 
                task.created_by == user or
                task.project.assignments.filter(
                    user=user, 
                    role__in=['manager', 'owner']
                ).exists()
            )
            
            if not is_task_participant:
                # Allow collaborators to comment if they have project access
                assignment = task.project.assignments.filter(user=user).first()
                if not assignment or assignment.role == 'viewer':
                    raise serializers.ValidationError(
                        "Solo los participantes de la tarea pueden comentar."
                    )
        
        return attrs
    
    def create(self, validated_data):
        """Create comment with author and task."""
        validated_data['author'] = self.context['request'].user
        validated_data['task'] = self.context['task']
        return TaskComment.objects.create(**validated_data)


class CommentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating comments."""
    
    class Meta:
        model = TaskComment
        fields = ('content',)
    
    def validate_content(self, value):
        """Validate comment content."""
        if not value.strip():
            raise serializers.ValidationError(
                "El comentario no puede estar vacío."
            )
        return value.strip()


class AssignTaskSerializer(serializers.Serializer):
    """Serializer for assigning tasks to users."""
    
    assigned_to_id = serializers.IntegerField(allow_null=True)
    
    def validate_assigned_to_id(self, value):
        """Validate assigned user exists and has access to project."""
        if value is not None:
            try:
                user = User.objects.get(id=value, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "Usuario no encontrado o inactivo."
                )
            
            # Check if user has access to the task's project
            task = self.context['task']
            if not task.project.assignments.filter(user=user).exists():
                raise serializers.ValidationError(
                    "El usuario debe tener acceso al proyecto."
                )
        
        return value


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating task status."""
    
    status = serializers.ChoiceField(choices=Task.Status.choices)
    
    def validate_status(self, value):
        """Validate status transition."""
        task = self.context['task']
        current_status = task.status
        
        # Define valid status transitions
        valid_transitions = {
            'pending': ['in_progress', 'completed'],
            'in_progress': ['pending', 'completed'],
            'completed': ['pending', 'in_progress']
        }
        
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"No se puede cambiar de '{current_status}' a '{value}'."
            )
        
        return value