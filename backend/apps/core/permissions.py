from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Se requiere rol de administrador."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role == "ADMIN")