from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Notification
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationCreateSerializer, NotificationUpdateSerializer,
    BulkNotificationUpdateSerializer, NotificationStatsSerializer,
    NotificationPreferencesSerializer
)
from apps.shared.permissions import IsNotificationRecipient


@extend_schema_view(
    list=extend_schema(tags=['Sistema de Notificaciones'], summary='Listar notificaciones'),
    create=extend_schema(tags=['Sistema de Notificaciones'], summary='Crear notificación'),
    retrieve=extend_schema(tags=['Sistema de Notificaciones'], summary='Obtener notificación'),
    update=extend_schema(tags=['Sistema de Notificaciones'], summary='Actualizar notificación'),
    partial_update=extend_schema(tags=['Sistema de Notificaciones'], summary='Actualización parcial de notificación'),
    destroy=extend_schema(tags=['Sistema de Notificaciones'], summary='Eliminar notificación'),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de notificaciones.
    
    Permite a los usuarios ver y gestionar sus notificaciones.
    Los usuarios solo pueden acceder a sus propias notificaciones.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsNotificationRecipient]
    
    class Meta:
        tags = ['Notificaciones']
    
    def get_queryset(self):
        """Get notifications for the current user."""
        user = self.request.user
        
        if user.is_superuser:
            return Notification.objects.all().select_related('recipient')
        
        return Notification.objects.filter(
            recipient=user
        ).select_related('recipient')
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return NotificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        elif self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    def list(self, request, *args, **kwargs):
        """List notifications with filtering options."""
        queryset = self.get_queryset()
        
        # Filter by read status
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_read=is_read_bool)
        
        # Filter by notification type
        notification_type = request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by date range
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Search in title and message
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(message__icontains=search)
            )
        
        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create notification (admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los administradores pueden crear notificaciones.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Marcar notificación como leída')
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Marcar notificación como no leída')
    @action(detail=True, methods=['patch'])
    def mark_as_unread(self, request, pk=None):
        """Mark notification as unread."""
        notification = self.get_object()
        notification.is_read = False
        notification.read_at = None
        notification.save()
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Marcar todas las notificaciones como leídas')
    @action(detail=False, methods=['patch'])
    def mark_all_as_read(self, request):
        """Mark all user notifications as read."""
        user = request.user
        updated_count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{updated_count} notificaciones marcadas como leídas.',
            'updated_count': updated_count
        })
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Actualización masiva de notificaciones')
    @action(detail=False, methods=['patch'])
    def bulk_update(self, request):
        """Bulk update notifications."""
        serializer = BulkNotificationUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            is_read = serializer.validated_data.get('is_read')
            
            # Filter notifications to only user's own
            queryset = self.get_queryset().filter(id__in=notification_ids)
            
            update_data = {}
            if is_read is not None:
                update_data['is_read'] = is_read
                if is_read:
                    update_data['read_at'] = timezone.now()
                else:
                    update_data['read_at'] = None
            
            updated_count = queryset.update(**update_data)
            
            return Response({
                'message': f'{updated_count} notificaciones actualizadas.',
                'updated_count': updated_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Eliminar notificaciones leídas')
    @action(detail=False, methods=['delete'])
    def delete_read(self, request):
        """Delete all read notifications for the user."""
        user = request.user
        deleted_count, _ = Notification.objects.filter(
            recipient=user,
            is_read=True
        ).delete()
        
        return Response({
            'message': f'{deleted_count} notificaciones leídas eliminadas.',
            'deleted_count': deleted_count
        })
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Eliminar notificaciones antiguas')
    @action(detail=False, methods=['delete'])
    def delete_old(self, request):
        """Delete notifications older than 30 days."""
        user = request.user
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count, _ = Notification.objects.filter(
            recipient=user,
            created_at__lt=cutoff_date
        ).delete()
        
        return Response({
            'message': f'{deleted_count} notificaciones antiguas eliminadas.',
            'deleted_count': deleted_count
        })
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Obtener cantidad de notificaciones no leídas')
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        user = request.user
        count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
        
        return Response({'unread_count': count})
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Obtener notificaciones recientes')
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications (last 10)."""
        user = request.user
        notifications = Notification.objects.filter(
            recipient=user
        ).order_by('-created_at')[:10]
        
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Obtener notificaciones no leídas')
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications for the user."""
        user = request.user
        notifications = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).order_by('-created_at')
        
        # Aplicar paginación si es necesario
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = NotificationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['Sistema de Notificaciones'], summary='Obtener estadísticas de notificaciones')
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics."""
        user = request.user
        notifications = Notification.objects.filter(recipient=user)
        
        total_notifications = notifications.count()
        unread_notifications = notifications.filter(is_read=False).count()
        read_notifications = notifications.filter(is_read=True).count()
        
        # Notifications by type
        notifications_by_type = dict(
            notifications.values('notification_type').annotate(
                count=Count('id')
            ).values_list('notification_type', 'count')
        )
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_notifications = notifications.filter(
            created_at__gte=week_ago
        ).count()
        
        stats_data = {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'read_notifications': read_notifications,
            'notifications_by_type': notifications_by_type,
            'recent_notifications': recent_notifications
        }
        
        serializer = NotificationStatsSerializer(data=stats_data)
        serializer.is_valid()
        return Response(serializer.data)
