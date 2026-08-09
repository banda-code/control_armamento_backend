from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import UserRole


class OrganizationPermission(BasePermission):
    """
    Todos los usuarios autenticados pueden consultar los catálogos
    permitidos. Solo el Administrador puede crear o modificar.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return (
            request.user.is_superuser
            or request.user.role == UserRole.ADMINISTRATOR
        )
