from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

from .models import Project, ProjectAssignment
from apps.authentication.serializers import UserSerializer

User = get_user_model()


class ProjectAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for project assignments."""
    
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ProjectAssignment
        fields = (
            'id', 'user', 'user_id', 'assigned_at', 'assigned_by'
        )
        read_only_fields = ('id', 'assigned_at', 'assigned_by')
    
    def validate_user_id(self, value):
        """Validate user exists and is active."""
        try:
            user = User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Usuario no encontrado o inactivo."
            )
        return value


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for projects."""
    
    created_by = UserSerializer(read_only=True)
    assignments = ProjectAssignmentSerializer(many=True, read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status',
            'start_date', 'end_date', 'created_by', 'created_at',
            'updated_at', 'assignments', 'progress_percentage',
            'is_overdue', 'days_remaining'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        """Validate project dates."""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({
                    'end_date': 'La fecha de finalización debe ser posterior a la fecha de inicio.'
                })
            
            # For new projects, start date should not be in the past
            if not self.instance and start_date < date.today():
                raise serializers.ValidationError({
                    'start_date': 'La fecha de inicio no puede ser anterior a hoy.'
                })
        
        return attrs
    
    def validate_name(self, value):
        """Validate project name uniqueness."""
        queryset = Project.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un proyecto con este nombre."
            )
        
        return value


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating projects with assignments."""
    
    assignments = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="Lista de asignaciones: [{'user_id': 1}, ...]"
    )
    
    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status',
            'start_date', 'end_date', 'assignments'
        )
        read_only_fields = ('id',)
    
    def validate(self, attrs):
        """Validate project data and assignments."""
        # Validate dates
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({
                    'end_date': 'La fecha de finalización debe ser posterior a la fecha de inicio.'
                })
            
            if start_date < date.today():
                raise serializers.ValidationError({
                    'start_date': 'La fecha de inicio no puede ser anterior a hoy.'
                })
        
        # Validate assignments
        assignments = attrs.get('assignments', [])
        if assignments:
            user_ids = []
            for assignment in assignments:
                if 'user_id' not in assignment:
                    raise serializers.ValidationError({
                        'assignments': 'Cada asignación debe incluir user_id.'
                    })
                
                user_id = assignment['user_id']
                if user_id in user_ids:
                    raise serializers.ValidationError({
                        'assignments': f'El usuario {user_id} está duplicado en las asignaciones.'
                    })
                user_ids.append(user_id)
                
                # Validate user exists
                if not User.objects.filter(id=user_id, is_active=True).exists():
                    raise serializers.ValidationError({
                        'assignments': f'Usuario {user_id} no encontrado o inactivo.'
                    })
                

        
        return attrs
    
    def create(self, validated_data):
        """Create project with assignments."""
        assignments_data = validated_data.pop('assignments', [])
        
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        
        project = Project.objects.create(**validated_data)
        
        # Create assignments
        for assignment_data in assignments_data:
            ProjectAssignment.objects.create(
                project=project,
                user_id=assignment_data['user_id'],
                assigned_by=self.context['request'].user
            )
        
        return project


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating projects."""
    
    # Hacer que las fechas sean opcionales para actualizaciones parciales
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    
    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status',
            'start_date', 'end_date'
        )
        read_only_fields = ('id',)
    
    def validate(self, attrs):
        """Validate project update data."""
        start_date = attrs.get('start_date', self.instance.start_date)
        end_date = attrs.get('end_date', self.instance.end_date)
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({
                    'end_date': 'La fecha de finalización debe ser posterior a la fecha de inicio.'
                })
        
        return attrs
    
    def validate_name(self, value):
        """Validate project name uniqueness."""
        queryset = Project.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un proyecto con este nombre."
            )
        
        return value


class ProjectListSerializer(serializers.ModelSerializer):
    """Simplified serializer for project lists."""
    
    created_by = serializers.StringRelatedField()
    progress_percentage = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    in_progress_tasks = serializers.SerializerMethodField()
    pending_tasks = serializers.SerializerMethodField()
    overdue_tasks = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'status',
            'start_date', 'end_date', 'created_by', 'created_at',
            'progress_percentage', 'is_overdue', 'days_remaining',
            'total_tasks', 'completed_tasks', 'in_progress_tasks',
            'pending_tasks', 'overdue_tasks', 'total_members'
        )
    
    def get_total_tasks(self, obj):
        """Get total number of tasks in project."""
        return obj.tasks.count()
    
    def get_completed_tasks(self, obj):
        """Get number of completed tasks in project."""
        return obj.tasks.filter(status='completed').count()
    
    def get_in_progress_tasks(self, obj):
        """Get number of in progress tasks in project."""
        return obj.tasks.filter(status='in_progress').count()
    
    def get_pending_tasks(self, obj):
        """Get number of pending tasks in project."""
        return obj.tasks.filter(status='pending').count()
    
    def get_overdue_tasks(self, obj):
        """Get number of overdue tasks in project."""
        from datetime import date
        return obj.tasks.filter(
            due_date__lt=date.today(),
            status__in=['pending', 'in_progress']
        ).count()
    
    def get_total_members(self, obj):
        """Get total number of members in project."""
        return obj.assignments.count()


class ProjectStatsSerializer(serializers.Serializer):
    """Serializer for project statistics."""
    
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    completed_projects = serializers.IntegerField()
    overdue_projects = serializers.IntegerField()
    projects_by_status = serializers.DictField()
    recent_projects = ProjectListSerializer(many=True)


class AssignUserToProjectSerializer(serializers.Serializer):
    """Serializer for assigning users to projects."""
    
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        """Validate user exists and is active."""
        try:
            user = User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Usuario no encontrado o inactivo."
            )
        return value
    
    def validate(self, attrs):
        """Validate assignment doesn't already exist."""
        project = self.context['project']
        user_id = attrs['user_id']
        
        if ProjectAssignment.objects.filter(
            project=project,
            user_id=user_id
        ).exists():
            raise serializers.ValidationError(
                "El usuario ya está asignado a este proyecto."
            )
        
        return attrs