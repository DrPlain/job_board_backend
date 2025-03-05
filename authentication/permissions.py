from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Custom permission to restrict access to admin users only.

    Checks if the authenticated user has the 'admin' role.
    """
    def has_permission(self, request, view):
        """
        Check if the user is authenticated and has admin role.

        Args:
            request: The incoming HTTP request.
            view: The view being accessed.

        Returns:
            bool: True if the user is an admin, False otherwise.
        """
        return request.user.is_authenticated and request.user.role == 'admin'
    

class IsEmployer(BasePermission):
    """Allow only Employers to post and manage jobs."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'employer'

class IsJobSeeker(BasePermission):
    """Allow only Job Seekers to apply for jobs."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'job_seeker'

class IsJobOwner(BasePermission):
    """Allow only the employer who posted the job to edit/delete it."""
    def has_object_permission(self, request, view, obj):
        return request.user == obj.employer
