from rest_framework.permissions import BasePermission

from .models import UserRole


class IsAdministrator(BasePermission):
    message = "Solo el Administrador puede realizar esta operación."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role == UserRole.ADMINISTRATOR
            )
        )
