from rest_framework import permissions
from apps.projects.models import ProjectAssignment


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners of an object to edit it."""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj.created_by == request.user


class IsProjectMember(permissions.BasePermission):
    """Custom permission to check if user is a member of the project."""
    
    def has_permission(self, request, view):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # For project-related views, check if user has access
        if hasattr(view, 'get_project'):
            project = view.get_project()
            if project:
                return ProjectAssignment.objects.filter(
                    project=project,
                    user=request.user
                ).exists()
        
        return True
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Check if user has access to the project
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'assignments'):
            project = obj
        else:
            return True
        
        return ProjectAssignment.objects.filter(
            project=project,
            user=request.user
        ).exists()


class IsProjectManagerOrReadOnly(permissions.BasePermission):
    """Custom permission for project managers."""
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Read permissions for project members
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'project'):
                project = obj.project
            elif hasattr(obj, 'assignments'):
                project = obj
            else:
                return True
            
            return ProjectAssignment.objects.filter(
                project=project,
                user=request.user
            ).exists()
        
        # Write permissions only for project managers and owners
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'assignments'):
            project = obj
        else:
            return obj.created_by == request.user
        
        # Check if user is project manager or owner
        assignment = ProjectAssignment.objects.filter(
            project=project,
            user=request.user
        ).first()
        
        if assignment:
            return assignment.role in ['manager', 'owner'] or project.created_by == request.user
        
        return False


class IsAssignedOrProjectManager(permissions.BasePermission):
    """Custom permission for tasks - assigned user or project manager can edit."""
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Read permissions for project members
        if request.method in permissions.SAFE_METHODS:
            return ProjectAssignment.objects.filter(
                project=obj.project,
                user=request.user
            ).exists()
        
        # Write permissions for:
        # 1. Task creator
        # 2. Assigned user
        # 3. Project manager/owner
        if obj.created_by == request.user or obj.assigned_to == request.user:
            return True
        
        # Check if user is project manager or owner
        assignment = ProjectAssignment.objects.filter(
            project=obj.project,
            user=request.user
        ).first()
        
        if assignment:
            return assignment.role in ['manager', 'owner'] or obj.project.created_by == request.user
        
        return False


class IsCommentAuthorOrReadOnly(permissions.BasePermission):
    """Custom permission for comments - only author can edit/delete."""
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Read permissions for project members
        if request.method in permissions.SAFE_METHODS:
            return ProjectAssignment.objects.filter(
                project=obj.task.project,
                user=request.user
            ).exists()
        
        # Write permissions only for comment author
        return obj.author == request.user


class IsNotificationRecipient(permissions.BasePermission):
    """Custom permission for notifications - only recipient can access."""
    
    def has_object_permission(self, request, view, obj):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Only recipient can access their notifications
        return obj.recipient == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """Custom permission for admin-only write operations."""
    
    def has_permission(self, request, view):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions only for admin users
        return request.user.is_staff or request.user.is_superuser


class CanManageProjectAssignments(permissions.BasePermission):
    """Custom permission for managing project assignments."""
    
    def has_permission(self, request, view):
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # For assignment management, check if user is project manager
        if hasattr(view, 'get_project'):
            project = view.get_project()
            if project:
                # Check if user is project owner
                if project.created_by == request.user:
                    return True
                
                # Check if user is project manager
                assignment = ProjectAssignment.objects.filter(
                    project=project,
                    user=request.user,
                    role__in=['manager', 'owner']
                ).first()
                
                return assignment is not None
        
        return False