from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import date, timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Project, ProjectAssignment
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectUpdateSerializer,
    ProjectListSerializer, ProjectStatsSerializer, ProjectAssignmentSerializer,
    AssignUserToProjectSerializer
)
from apps.shared.permissions import (
    IsProjectMember, IsProjectManagerOrReadOnly, CanManageProjectAssignments
)


@extend_schema_view(
    list=extend_schema(tags=['Gestión de Proyectos'], summary='Listar proyectos'),
    create=extend_schema(tags=['Gestión de Proyectos'], summary='Crear proyecto'),
    retrieve=extend_schema(tags=['Gestión de Proyectos'], summary='Obtener proyecto'),
    update=extend_schema(tags=['Gestión de Proyectos'], summary='Actualizar proyecto'),
    partial_update=extend_schema(tags=['Gestión de Proyectos'], summary='Actualización parcial de proyecto'),
    destroy=extend_schema(tags=['Gestión de Proyectos'], summary='Eliminar proyecto'),
)
class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de proyectos.
    
    Proporciona operaciones CRUD completas para proyectos, incluyendo:
    - Gestión de asignaciones de usuarios
    - Estadísticas de proyectos
    - Filtrado por estado y usuario
    """
    
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]
    
    class Meta:
        tags = ['Proyectos']
    
    def get_queryset(self):
        """Get projects accessible to the current user."""
        user = self.request.user
        
        if user.is_superuser:
            return Project.objects.all().select_related('created_by').prefetch_related(
                'assignments__user', 'tasks'
            )
        
        # Get projects where user is assigned
        return Project.objects.filter(
            assignments__user=user
        ).select_related('created_by').prefetch_related(
            'assignments__user', 'tasks'
        ).distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return ProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProjectUpdateSerializer
        elif self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer
    
    def get_permissions(self):
        """Get permissions based on action."""
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrReadOnly]
        else:
            permission_classes = [permissions.IsAuthenticated, IsProjectMember]
        
        return [permission() for permission in permission_classes]
    
    def get_project(self):
        """Helper method to get project for permission checks."""
        if hasattr(self, 'kwargs') and 'pk' in self.kwargs:
            return get_object_or_404(Project, pk=self.kwargs['pk'])
        return None
    
    def perform_create(self, serializer):
        """Create project and assign creator as owner."""
        project = serializer.save(created_by=self.request.user)
        
        # Assign creator as project owner
        ProjectAssignment.objects.create(
            project=project,
            user=self.request.user,
            assigned_by=self.request.user
        )
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Obtener asignaciones del proyecto')
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Get project assignments."""
        project = self.get_object()
        assignments = project.assignments.select_related('user', 'assigned_by')
        serializer = ProjectAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Asignar usuario al proyecto')
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanManageProjectAssignments])
    def assign_user(self, request, pk=None):
        """Assign user to project."""
        project = self.get_object()
        serializer = AssignUserToProjectSerializer(
            data=request.data,
            context={'project': project, 'request': request}
        )
        
        if serializer.is_valid():
            assignment = ProjectAssignment.objects.create(
                project=project,
                user_id=serializer.validated_data['user_id'],
                assigned_by=request.user
            )
            
            response_serializer = ProjectAssignmentSerializer(assignment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Actualizar asignación de proyecto')
    @action(detail=True, methods=['patch'], url_path='assignments/(?P<assignment_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated, CanManageProjectAssignments])
    def update_assignment(self, request, pk=None, assignment_id=None):
        """Update project assignment."""
        project = self.get_object()
        assignment = get_object_or_404(
            ProjectAssignment,
            id=assignment_id,
            project=project
        )
        
        # For now, just return the assignment as role field doesn't exist
        response_serializer = ProjectAssignmentSerializer(assignment)
        return Response(response_serializer.data)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Remover usuario del proyecto')
    @action(detail=True, methods=['delete'], url_path='assignments/(?P<assignment_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated, CanManageProjectAssignments])
    def remove_assignment(self, request, pk=None, assignment_id=None):
        """Remove user from project."""
        project = self.get_object()
        assignment = get_object_or_404(
            ProjectAssignment,
            id=assignment_id,
            project=project
        )
        
        # Prevent removing the project creator
        if assignment.user == project.created_by:
            return Response(
                {'error': 'No se puede eliminar al propietario del proyecto.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Obtener tareas del proyecto')
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """Get project tasks."""
        project = self.get_object()
        tasks = project.tasks.select_related('created_by', 'assigned_to').prefetch_related('comments')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        
        # Filter by assigned user if provided
        assigned_to = request.query_params.get('assigned_to')
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)
        
        from apps.tasks.serializers import TaskListSerializer
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Obtener estadísticas del proyecto')
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get project statistics."""
        project = self.get_object()
        
        # Task statistics
        tasks = project.tasks.all()
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        pending_tasks = tasks.filter(status='pending').count()
        overdue_tasks = tasks.filter(
            due_date__lt=date.today(),
            status__in=['pending', 'in_progress']
        ).count()
        
        # Assignment statistics
        total_members = project.assignments.count()
        
        # Progress calculation
        progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        stats_data = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'pending_tasks': pending_tasks,
            'overdue_tasks': overdue_tasks,
            'total_members': total_members,
            'progress_percentage': round(progress, 2),
            'is_overdue': project.is_overdue,
            'days_remaining': project.days_remaining
        }
        
        return Response(stats_data)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Obtener mis proyectos')
    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """Get current user's projects."""
        user = request.user
        projects = self.get_queryset().filter(
            Q(created_by=user) | Q(assignments__user=user)
        ).distinct()
        
        serializer = ProjectListSerializer(projects, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Gestión de Proyectos'], summary='Obtener estadísticas del dashboard')
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for projects."""
        user = request.user
        
        if user.is_superuser:
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(assignments__user=user).distinct()
        
        total_projects = projects.count()
        active_projects = projects.filter(status='active').count()
        completed_projects = projects.filter(status='completed').count()
        overdue_projects = projects.filter(
            end_date__lt=date.today(),
            status__in=['active', 'planning']
        ).count()
        
        # Projects by status
        projects_by_status = dict(
            projects.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )
        
        # Recent projects
        recent_projects = projects.order_by('-created_at')[:5]
        
        stats_data = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'overdue_projects': overdue_projects,
            'projects_by_status': projects_by_status,
            'recent_projects': ProjectListSerializer(recent_projects, many=True).data
        }
        
        serializer = ProjectStatsSerializer(data=stats_data)
        serializer.is_valid()
        return Response(serializer.data)