"""
Custom DRF permission classes for role-based access control.
Implements FR-UA-02 through FR-UA-06.
"""

from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permission class: Only Admin users can access.
    FR-UA-02: Admin has full access to all modules.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsStaff(permissions.BasePermission):
    """
    Permission class: Only Staff users can access.
    FR-UA-03: Staff has access to patient management, calendar, call logs.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff_role


class IsDoctor(permissions.BasePermission):
    """
    Permission class: Only Doctor users can access.
    FR-UA-04: Doctor has access to own slot management and schedule.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_doctor


class IsReadOnly(permissions.BasePermission):
    """
    Permission class: Read-Only users can only view data.
    FR-UA-05: Read-Only users have view-only access.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Read-only users can only perform safe methods (GET, HEAD, OPTIONS)
        if request.user.is_readonly:
            return request.method in permissions.SAFE_METHODS
        
        return True


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission class: Admin or Staff users can access.
    Used for patient management, call logs, etc.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_admin or request.user.is_staff_role)
        )


class IsAdminOrOwner(permissions.BasePermission):
    """
    Permission class: Admin can access all, others can only access their own data.
    Used for doctor profile editing (FR-DM-03).
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.is_admin:
            return True
        
        # Check if the object has a 'user' attribute and it matches the request user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False
