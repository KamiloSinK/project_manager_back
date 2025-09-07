from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]

# Endpoints disponibles:
# GET /api/notifications/ - Listar notificaciones con filtros
# POST /api/notifications/ - Crear nueva notificación (solo admin)
# GET /api/notifications/{id}/ - Obtener detalles de notificación
# PUT /api/notifications/{id}/ - Actualizar notificación
# PATCH /api/notifications/{id}/ - Actualización parcial de notificación
# DELETE /api/notifications/{id}/ - Eliminar notificación
# PATCH /api/notifications/{id}/mark_as_read/ - Marcar notificación como leída
# PATCH /api/notifications/{id}/mark_as_unread/ - Marcar notificación como no leída
# PATCH /api/notifications/mark_all_as_read/ - Marcar todas las notificaciones como leídas
# PATCH /api/notifications/bulk_update/ - Actualización masiva de notificaciones
# DELETE /api/notifications/delete_read/ - Eliminar todas las notificaciones leídas
# DELETE /api/notifications/delete_old/ - Eliminar notificaciones de más de 30 días
# GET /api/notifications/unread_count/ - Obtener cantidad de notificaciones no leídas
# GET /api/notifications/recent/ - Obtener notificaciones recientes
# GET /api/notifications/stats/ - Obtener estadísticas de notificaciones