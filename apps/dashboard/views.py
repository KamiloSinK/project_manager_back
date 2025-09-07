from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count
from django.utils import timezone
from apps.projects.models import Project
from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=['Dashboard'],
    summary='Obtener estadísticas del dashboard',
    description='Retorna estadísticas de proyectos basadas en el rol del usuario. Los administradores ven todas las estadísticas, otros usuarios solo ven los proyectos donde están asignados.',
    responses={
        200: {
            'type': 'object',
            'properties': {
                'total_projects': {'type': 'integer', 'description': 'Total de proyectos'},
                'completed_projects': {'type': 'integer', 'description': 'Proyectos completados'},
                'in_progress_projects': {'type': 'integer', 'description': 'Proyectos en progreso'},
                'overdue_projects': {'type': 'integer', 'description': 'Proyectos retrasados'},
                'pending_projects': {'type': 'integer', 'description': 'Proyectos pendientes'},
                'cancelled_projects': {'type': 'integer', 'description': 'Proyectos cancelados'}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Obtiene estadísticas de proyectos basadas en el rol del usuario.
    
    - Admin: Ve todas las estadísticas del sistema
    - Otros usuarios: Solo ven estadísticas de proyectos donde están asignados
    """
    user = request.user
    
    # Filtrar proyectos según el rol del usuario
    if user.role == 'admin':
        # Los administradores ven todos los proyectos
        projects_queryset = Project.objects.all()
    else:
        # Otros usuarios solo ven proyectos donde están asignados o que han creado
        projects_queryset = Project.objects.filter(
            Q(created_by=user) | Q(assignments__user=user)
        ).distinct()
    
    # Calcular estadísticas
    total_projects = projects_queryset.count()
    
    # Proyectos por estado
    completed_projects = projects_queryset.filter(status='completed').count()
    in_progress_projects = projects_queryset.filter(status='in_progress').count()
    pending_projects = projects_queryset.filter(status='pending').count()
    cancelled_projects = projects_queryset.filter(status='cancelled').count()
    
    # Proyectos retrasados (fecha de fin pasada y no completados)
    current_date = timezone.now().date()
    overdue_projects = projects_queryset.filter(
        end_date__lt=current_date,
        status__in=['pending', 'in_progress']
    ).count()
    
    stats = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'in_progress_projects': in_progress_projects,
        'overdue_projects': overdue_projects,
        'pending_projects': pending_projects,
        'cancelled_projects': cancelled_projects
    }
    
    return Response(stats, status=status.HTTP_200_OK)
