# permissions.py
from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access the endpoint.
    """
    def has_permission(self, request, view):
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if the user has admin privileges (is_staff or is_superuser)
        return request.user.is_staff  # Adjust based on your needs
