from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'', TaskViewSet, basename='task')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]

# Endpoints disponibles:
# GET /api/tasks/ - Listar tareas con filtros
# POST /api/tasks/ - Crear nueva tarea
# GET /api/tasks/{id}/ - Obtener detalles de tarea
# PUT /api/tasks/{id}/ - Actualizar tarea
# PATCH /api/tasks/{id}/ - Actualización parcial de tarea
# DELETE /api/tasks/{id}/ - Eliminar tarea
# GET /api/tasks/{id}/comments/ - Obtener comentarios de tarea
# POST /api/tasks/{id}/add_comment/ - Agregar comentario a tarea
# PATCH /api/tasks/{id}/assign/ - Asignar tarea a usuario
# PATCH /api/tasks/{id}/update_status/ - Actualizar estado de tarea
# GET /api/tasks/my_tasks/ - Obtener tareas del usuario actual
# GET /api/tasks/dashboard_stats/ - Obtener estadísticas de tareas
# GET /api/tasks/comments/ - Listar comentarios con filtros
# POST /api/tasks/comments/ - Crear nuevo comentario
# GET /api/tasks/comments/{id}/ - Obtener detalles de comentario
# PUT /api/tasks/comments/{id}/ - Actualizar comentario
# PATCH /api/tasks/comments/{id}/ - Actualización parcial de comentario
# DELETE /api/comments/{id}/ - Delete comment