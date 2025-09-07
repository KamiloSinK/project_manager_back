from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Task, TaskComment
from .serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer,
    TaskListSerializer, TaskStatsSerializer, CommentSerializer,
    CommentCreateSerializer, CommentUpdateSerializer,
    AssignTaskSerializer, TaskStatusUpdateSerializer
)
from apps.shared.permissions import (
        IsProjectMember, IsAssignedOrProjectManager, IsCommentAuthorOrReadOnly
    )
from apps.notifications.models import Notification
from apps.projects.models import ProjectAssignment


@extend_schema_view(
    list=extend_schema(tags=['Gestión de Tareas'], summary='Listar tareas'),
    create=extend_schema(tags=['Gestión de Tareas'], summary='Crear tarea'),
    retrieve=extend_schema(tags=['Gestión de Tareas'], summary='Obtener tarea'),
    update=extend_schema(tags=['Gestión de Tareas'], summary='Actualizar tarea'),
    partial_update=extend_schema(tags=['Gestión de Tareas'], summary='Actualización parcial de tarea'),
    destroy=extend_schema(tags=['Gestión de Tareas'], summary='Eliminar tarea'),
)
class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de tareas.
    
    Proporciona operaciones CRUD completas para tareas, incluyendo:
    - Asignación de tareas a usuarios
    - Actualización de estado
    - Filtrado por proyecto, estado, prioridad y usuario
    - Estadísticas de tareas
    """
    
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]
    
    class Meta:
        tags = ['Tareas']
    
    def get_queryset(self):
        """Get tasks accessible to the current user."""
        user = self.request.user
        
        if user.is_superuser:
            return Task.objects.all().select_related(
                'created_by', 'assigned_to', 'project'
            ).prefetch_related('comments__author')
        
        # Get tasks from projects where user is assigned
        return Task.objects.filter(
            project__assignments__user=user
        ).select_related(
            'created_by', 'assigned_to', 'project'
        ).prefetch_related('comments__author').distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        elif self.action == 'list':
            return TaskListSerializer
        return TaskSerializer
    
    def get_permissions(self):
        """Get permissions based on action."""
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAssignedOrProjectManager]
        else:
            permission_classes = [permissions.IsAuthenticated, IsProjectMember]
        
        return [permission() for permission in permission_classes]
    
    def get_project(self):
        """Helper method to get project for permission checks."""
        if hasattr(self, 'get_object'):
            try:
                task = self.get_object()
                return task.project
            except:
                pass
        return None
    
    def list(self, request, *args, **kwargs):
        """List tasks with filtering options."""
        queryset = self.get_queryset()
        
        # Filter by project
        project_id = request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority_filter = request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        # Filter by assigned user
        assigned_to = request.query_params.get('assigned_to')
        if assigned_to:
            if assigned_to == 'me':
                queryset = queryset.filter(assigned_to=request.user)
            else:
                queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by due date
        due_date = request.query_params.get('due_date')
        if due_date:
            if due_date == 'overdue':
                queryset = queryset.filter(
                    due_date__lt=date.today(),
                    status__in=['pending', 'in_progress']
                )
            elif due_date == 'today':
                queryset = queryset.filter(due_date=date.today())
            elif due_date == 'this_week':
                today = date.today()
                week_end = today + timedelta(days=7-today.weekday())
                queryset = queryset.filter(due_date__lte=week_end)
        
        # Search by title or description
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # Order by
        ordering = request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Obtener comentarios de la tarea')
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get task comments."""
        task = self.get_object()
        comments = task.comments.select_related('author').order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Agregar comentario a la tarea')
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add comment to task."""
        task = self.get_object()
        serializer = CommentCreateSerializer(
            data=request.data,
            context={'task': task, 'request': request}
        )
        
        if serializer.is_valid():
            comment = serializer.save()
            response_serializer = CommentSerializer(comment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Asignar tarea a usuario')
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsAssignedOrProjectManager])
    def assign(self, request, pk=None):
        """Assign task to user."""
        task = self.get_object()
        serializer = AssignTaskSerializer(
            data=request.data,
            context={'task': task, 'request': request}
        )
        
        if serializer.is_valid():
            task.assigned_to_id = serializer.validated_data['assigned_to_id']
            task.save()
            
            response_serializer = TaskSerializer(task)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Actualizar estado de la tarea')
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update task status."""
        task = self.get_object()
        
        # Check if user can update status
        user = request.user
        if not (user.is_superuser or task.assigned_to == user or task.created_by == user):
            # Check if user is project manager
            assignment = ProjectAssignment.objects.filter(
                project=task.project,
                user=user,
                role__in=['manager', 'owner']
            ).first()
            
            if not assignment:
                return Response(
                    {'error': 'No tienes permisos para actualizar el estado de esta tarea.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = TaskStatusUpdateSerializer(
            data=request.data,
            context={'task': task, 'request': request}
        )
        
        if serializer.is_valid():
            task.status = serializer.validated_data['status']
            task.save()
            
            response_serializer = TaskSerializer(task)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Cambiar estado de tarea (cualquier usuario)')
    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        """Change task status - accessible to any authenticated user."""
        task = self.get_object()
        
        # Verificar que el usuario tenga acceso al proyecto
        if not (request.user.is_superuser or 
                ProjectAssignment.objects.filter(
                    project=task.project,
                    user=request.user
                ).exists()):
            return Response(
                {'error': 'No tienes acceso a este proyecto.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TaskStatusUpdateSerializer(
            data=request.data,
            context={'task': task, 'request': request}
        )
        
        if serializer.is_valid():
            old_status = task.status
            task.status = serializer.validated_data['status']
            task.save()
            
            # Crear notificación para el usuario asignado si es diferente
            if task.assigned_to and task.assigned_to != request.user:
                Notification.objects.create(
                    recipient=task.assigned_to,
                    sender=request.user,
                    notification_type='task_status_changed',
                    title=f'Estado de tarea actualizado',
                    message=f'El estado de la tarea "{task.name}" cambió de {old_status} a {task.status}',
                    related_object_type='task',
                    related_object_id=task.id
                )
            
            response_serializer = TaskSerializer(task)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Obtener mis tareas asignadas')
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get current user's assigned tasks."""
        user = request.user
        tasks = self.get_queryset().filter(assigned_to=user)
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        
        # Order by priority and due date
        tasks = tasks.order_by('due_date', '-priority')
        
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Gestión de Tareas'], summary='Obtener estadísticas del dashboard de tareas')
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for tasks."""
        user = request.user
        
        if user.is_superuser:
            tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(project__assignments__user=user).distinct()
        
        total_tasks = tasks.count()
        pending_tasks = tasks.filter(status='pending').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        completed_tasks = tasks.filter(status='completed').count()
        overdue_tasks = tasks.filter(
            due_date__lt=date.today(),
            status__in=['pending', 'in_progress']
        ).count()
        
        # Tasks by status
        tasks_by_status = dict(
            tasks.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )
        
        # Tasks by priority
        tasks_by_priority = dict(
            tasks.values('priority').annotate(
                count=Count('id')
            ).values_list('priority', 'count')
        )
        
        # My tasks
        my_tasks = tasks.filter(assigned_to=user).order_by('due_date')[:5]
        
        # Recent tasks
        recent_tasks = tasks.order_by('-created_at')[:5]
        
        stats_data = {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'tasks_by_status': tasks_by_status,
            'tasks_by_priority': tasks_by_priority,
            'my_tasks': TaskListSerializer(my_tasks, many=True).data,
            'recent_tasks': TaskListSerializer(recent_tasks, many=True).data
        }
        
        serializer = TaskStatsSerializer(data=stats_data)
        serializer.is_valid()
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['Gestión de Tareas'], summary='Listar comentarios'),
    create=extend_schema(tags=['Gestión de Tareas'], summary='Crear comentario'),
    retrieve=extend_schema(tags=['Gestión de Tareas'], summary='Obtener comentario'),
    update=extend_schema(tags=['Gestión de Tareas'], summary='Actualizar comentario'),
    partial_update=extend_schema(tags=['Gestión de Tareas'], summary='Actualización parcial de comentario'),
    destroy=extend_schema(tags=['Gestión de Tareas'], summary='Eliminar comentario'),
)
class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de comentarios de tareas.
    
    Permite a los usuarios agregar, editar y eliminar comentarios en tareas.
    Solo el autor del comentario puede editarlo o eliminarlo.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsCommentAuthorOrReadOnly]
    
    class Meta:
        tags = ['Comentarios']
    serializer_class = CommentSerializer
    
    def get_queryset(self):
        """Get comments accessible to the current user."""
        user = self.request.user
        
        if user.is_superuser:
            return TaskComment.objects.all().select_related('author', 'task__project')
        
        # Get comments from tasks in projects where user is assigned
        return TaskComment.objects.filter(
            task__project__assignments__user=user
        ).select_related('author', 'task__project').distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action in ['update', 'partial_update']:
            return CommentUpdateSerializer
        elif self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer
    
    def list(self, request, *args, **kwargs):
        """List comments with filtering by task."""
        queryset = self.get_queryset()
        
        # Filter by task with validation
        task_id = request.query_params.get('task')
        if task_id:
            try:
                task_id = int(task_id)
                # Validate task exists and user has access
                task = Task.objects.filter(
                    id=task_id,
                    project__assignments__user=request.user
                ).first()
                
                if not task and not request.user.is_superuser:
                    return Response(
                        {'error': 'Tarea no encontrada o sin permisos de acceso.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                queryset = queryset.filter(task_id=task_id)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'ID de tarea inválido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Order by creation date
        queryset = queryset.order_by('created_at')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create comment with enhanced validation."""
        # Validate task ID if provided
        task_id = request.data.get('task')
        if task_id:
            try:
                task_id = int(task_id)
                task = Task.objects.filter(
                    id=task_id,
                    project__assignments__user=request.user
                ).first()
                
                if not task and not request.user.is_superuser:
                    return Response(
                        {'error': 'Tarea no encontrada o sin permisos para comentar.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Add task to serializer context
                serializer = self.get_serializer(
                    data=request.data,
                    context={'task': task, 'request': request}
                )
                
                if serializer.is_valid():
                    comment = serializer.save()
                    
                    # Create notifications for task participants
                    try:
                        Notification.create_comment_notification(comment)
                    except Exception as e:
                        # Log error but don't fail comment creation
                        print(f"Error creating comment notification: {e}")
                    
                    response_serializer = CommentSerializer(comment)
                    return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            except (ValueError, TypeError):
                return Response(
                    {'error': 'ID de tarea inválido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {'error': 'ID de tarea es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def perform_update(self, serializer):
        """Update comment with validation."""
        comment = self.get_object()
        
        # Verify user can edit this comment
        if comment.author != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied('Solo puedes editar tus propios comentarios.')
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Delete comment with validation."""
        # Verify user can delete this comment
        if instance.author != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied('Solo puedes eliminar tus propios comentarios.')
        
        instance.delete()
