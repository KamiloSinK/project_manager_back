from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]

# Patrones de URL generados:
# GET    /api/projects/                     - Listar proyectos
# POST   /api/projects/                     - Crear proyecto
# GET    /api/projects/{id}/                - Obtener proyecto
# PUT    /api/projects/{id}/                - Actualizar proyecto
# PATCH  /api/projects/{id}/                - Actualización parcial del proyecto
# DELETE /api/projects/{id}/                - Eliminar proyecto
# GET    /api/projects/{id}/assignments/    - Obtener asignaciones del proyecto
# POST   /api/projects/{id}/assign_user/    - Asignar usuario al proyecto
# PATCH  /api/projects/{id}/assignments/{assignment_id}/ - Actualizar rol de asignación
# DELETE /api/projects/{id}/assignments/{assignment_id}/ - Eliminar asignación
# GET    /api/projects/{id}/tasks/          - Obtener tareas del proyecto
# GET    /api/projects/{id}/stats/          - Obtener estadísticas del proyecto
# GET    /api/projects/my_projects/         - Obtener proyectos del usuario actual
# GET    /api/projects/dashboard_stats/     - Obtener estadísticas del dashboard
