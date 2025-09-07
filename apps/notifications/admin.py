from django.contrib import admin
from django.utils.html import format_html
from django.db import models

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification model."""
    
    list_display = (
        'title', 'recipient', 'type', 'priority', 'is_read', 
        'sender', 'created_at', 'read_at'
    )
    list_filter = (
        'type', 'priority', 'is_read', 'created_at', 'read_at',
        'recipient', 'sender'
    )
    search_fields = (
        'title', 'message', 
        'recipient__email', 'recipient__first_name', 'recipient__last_name',
        'sender__email', 'sender__first_name', 'sender__last_name'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'message', 'type', 'priority')
        }),
        ('Destinatario y Remitente', {
            'fields': ('recipient', 'sender')
        }),
        ('Estado', {
            'fields': ('is_read', 'read_at')
        }),
        ('Objetos Relacionados', {
            'fields': ('related_project', 'related_task'),
            'classes': ('collapse',)
        }),
        ('Datos Adicionales', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    autocomplete_fields = ['recipient', 'sender', 'related_project', 'related_task']
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related(
            'recipient', 'sender', 'related_project', 'related_task'
        )
    
    def get_list_display(self, request):
        """Customize list display based on user permissions."""
        display = list(self.list_display)
        if not request.user.is_superuser:
            # Non-superusers don't need to see sender in list
            if 'sender' in display:
                display.remove('sender')
        return display
    
    def get_queryset(self, request):
        """Filter queryset based on user permissions."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see only their notifications or notifications they sent
            qs = qs.filter(
                models.Q(recipient=request.user) |
                models.Q(sender=request.user)
            ).distinct()
        return qs
    
    def has_add_permission(self, request):
        """Allow adding notifications."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow changing notifications with restrictions."""
        if obj:
            # Users can only modify their own notifications or ones they sent
            if not request.user.is_superuser:
                return obj.recipient == request.user or obj.sender == request.user
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting notifications with restrictions."""
        if obj:
            # Users can only delete their own notifications
            if not request.user.is_superuser:
                return obj.recipient == request.user
        return True
    
    def save_model(self, request, obj, form, change):
        """Set sender to current user if not set."""
        if not change and not obj.sender:  # Only for new objects without sender
            obj.sender = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected']
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} notificaciones marcadas como leídas.'
        )
    mark_as_read.short_description = 'Marcar como leídas'
    
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread."""
        updated = 0
        for notification in queryset:
            if notification.is_read:
                notification.mark_as_unread()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} notificaciones marcadas como no leídas.'
        )
    mark_as_unread.short_description = 'Marcar como no leídas'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions."""
        form = super().get_form(request, obj, **kwargs)
        
        if not request.user.is_superuser:
            # Non-superusers have limited access to certain fields
            if 'sender' in form.base_fields:
                form.base_fields['sender'].initial = request.user
                form.base_fields['sender'].disabled = True
            
            # Limit recipient choices to users in same projects
            if 'recipient' in form.base_fields:
                # Get users from projects where current user is assigned
                from apps.authentication.models import User
                accessible_users = User.objects.filter(
                    models.Q(project_assignments__project__assignments__user=request.user) |
                    models.Q(id=request.user.id)
                ).distinct()
                form.base_fields['recipient'].queryset = accessible_users
        
        return form
