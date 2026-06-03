from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Allows access only to users with the 'student' role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'student'


class IsBusiness(permissions.BasePermission):
    """
    Allows access only to users with the 'business' role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'business'


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to users with the 'admin' role or staff status.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser
        )
