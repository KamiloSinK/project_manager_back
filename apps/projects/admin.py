from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Project, ProjectAssignment


class ProjectAssignmentInline(admin.TabularInline):
    """Inline admin for project assignments."""
    model = ProjectAssignment
    extra = 1
    autocomplete_fields = ['user', 'assigned_by']
    readonly_fields = ('assigned_at',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for Project model."""
    
    list_display = (
        'name', 'status', 'created_by', 'start_date', 'end_date', 
        'progress_display', 'is_overdue_display', 'created_at'
    )
    list_filter = (
        'status', 'start_date', 'end_date', 'created_at', 'created_by'
    )
    search_fields = ('name', 'description', 'created_by__email', 'created_by__first_name', 'created_by__last_name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'status')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date')
        }),
        ('Creación', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['created_by']
    inlines = [ProjectAssignmentInline]
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('created_by').prefetch_related('assignments__user', 'tasks')
    
    def progress_display(self, obj):
        """Display project progress as a progress bar."""
        progress = obj.get_progress_percentage()
        color = 'success' if progress >= 75 else 'warning' if progress >= 50 else 'danger'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">' +
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">' +
            '{}%</div></div>',
            progress,
            '#28a745' if color == 'success' else '#ffc107' if color == 'warning' else '#dc3545',
            progress
        )
    progress_display.short_description = 'Progreso'
    
    def is_overdue_display(self, obj):
        """Display if project is overdue."""
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">Vencido</span>')
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


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for ProjectAssignment model."""
    
    list_display = (
        'project', 'user', 'assigned_by', 'assigned_at'
    )
    list_filter = (
        'assigned_at', 'project__status', 'assigned_by'
    )
    search_fields = (
        'project__name', 'user__email', 'user__first_name', 'user__last_name',
        'assigned_by__email', 'assigned_by__first_name', 'assigned_by__last_name'
    )
    ordering = ('-assigned_at',)
    date_hierarchy = 'assigned_at'
    
    autocomplete_fields = ['project', 'user', 'assigned_by']
    readonly_fields = ('assigned_at',)
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('project', 'user', 'assigned_by')
    
    def save_model(self, request, obj, form, change):
        """Set assigned_by to current user if not set."""
        if not change:  # Only for new objects
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)
