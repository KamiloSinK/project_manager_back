from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db import models

from .models import Task, TaskComment


class TaskCommentInline(admin.TabularInline):
    """Inline admin for task comments."""
    model = TaskComment
    extra = 1
    fields = ('author', 'content', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['author']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin configuration for Task model."""
    
    list_display = (
        'name', 'project', 'status', 'priority', 'assigned_to', 
        'due_date', 'is_overdue_display', 'created_by', 'created_at'
    )
    list_filter = (
        'status', 'priority', 'project', 'due_date', 'created_at', 
        'assigned_to', 'created_by'
    )
    search_fields = (
        'name', 'description', 'project__name', 
        'assigned_to__email', 'assigned_to__first_name', 'assigned_to__last_name',
        'created_by__email', 'created_by__first_name', 'created_by__last_name'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'project')
        }),
        ('Estado y Prioridad', {
            'fields': ('status', 'priority')
        }),
        ('Asignación', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Fechas', {
            'fields': ('due_date', 'completed_at')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    autocomplete_fields = ['project', 'assigned_to', 'created_by']
    inlines = [TaskCommentInline]
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related(
            'project', 'assigned_to', 'created_by'
        ).prefetch_related('comments')
    
    def is_overdue_display(self, obj):
        """Display if task is overdue."""
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">Vencida</span>')
        elif obj.is_urgent:
            return format_html('<span style="color: orange; font-weight: bold;">Urgente</span>')
        return format_html('<span style="color: green;">Al día</span>')
    is_overdue_display.short_description = 'Estado'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions."""
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            # Non-superusers can only assign themselves as created_by
            if 'created_by' in form.base_fields:
                form.base_fields['created_by'].initial = request.user
                form.base_fields['created_by'].disabled = True
        return form
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user if not set."""
        if not change:  # Only for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_list_filter(self, request):
        """Customize list filters based on user permissions."""
        filters = list(self.list_filter)
        if not request.user.is_superuser:
            # Non-superusers see only their related tasks
            filters = [f for f in filters if f != 'created_by']
        return filters
    
    def get_queryset(self, request):
        """Filter queryset based on user permissions."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see only tasks they created, are assigned to, or in projects they're assigned to
            qs = qs.filter(
                models.Q(created_by=request.user) |
                models.Q(assigned_to=request.user) |
                models.Q(project__assignments__user=request.user)
            ).distinct()
        return qs


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """Admin configuration for TaskComment model."""
    
    list_display = (
        'task', 'author', 'content_preview', 'created_at'
    )
    list_filter = (
        'created_at', 'author', 'task__project'
    )
    search_fields = (
        'content', 'task__name', 'task__project__name',
        'author__email', 'author__first_name', 'author__last_name'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Comentario', {
            'fields': ('task', 'author', 'content')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['task', 'author']
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related(
            'task', 'task__project', 'author'
        )
    
    def content_preview(self, obj):
        """Display a preview of the comment content."""
        if len(obj.content) > 50:
            return obj.content[:50] + '...'
        return obj.content
    content_preview.short_description = 'Contenido'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions."""
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            # Non-superusers can only assign themselves as author
            if 'author' in form.base_fields:
                form.base_fields['author'].initial = request.user
                form.base_fields['author'].disabled = True
        return form
    
    def save_model(self, request, obj, form, change):
        """Set author to current user if not set."""
        if not change:  # Only for new objects
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Filter queryset based on user permissions."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see only comments on tasks they have access to
            qs = qs.filter(
                models.Q(task__created_by=request.user) |
                models.Q(task__assigned_to=request.user) |
                models.Q(task__project__assignments__user=request.user) |
                models.Q(author=request.user)
            ).distinct()
        return qs
