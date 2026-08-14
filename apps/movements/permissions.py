from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)

from apps.accounts.models import UserRole
from apps.accounts.scopes import get_user_unit_id


READ_ROLES = {
    UserRole.ADMINISTRATOR,
    UserRole.NAVY_COMMAND,
    UserRole.UNIT_COMMANDER,
    UserRole.LOGISTICS_CHIEF,
    UserRole.ARMAMENT_OFFICER,
}


WRITE_ROLES = {
    UserRole.ADMINISTRATOR,
    UserRole.LOGISTICS_CHIEF,
    UserRole.ARMAMENT_OFFICER,
}


class SerializedMovementPermission(BasePermission):
    """
    Permisos para movimientos de materiales
    serializados de dotación de unidad.

    ADMINISTRATOR:
        - consulta global
        - registra salidas
        - registra retornos

    NAVY_COMMAND:
        - consulta global

    UNIT_COMMANDER:
        - consulta movimientos de su unidad

    LOGISTICS_CHIEF:
        - consulta de su unidad
        - registra salidas
        - registra retornos

    ARMAMENT_OFFICER:
        - consulta de su unidad
        - registra salidas
        - registra retornos
    """

    message = (
        "No tiene permiso para acceder "
        "o registrar este movimiento."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        # Superusuario técnico.
        if user.is_superuser:
            return True

        role = user.role

        if role not in READ_ROLES:
            return False

        # Consultas.
        if request.method in SAFE_METHODS:
            return True

        # No permitiremos eliminación.
        if request.method == "DELETE":
            return False

        # Salidas y retornos.
        return role in WRITE_ROLES

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        # Superusuario técnico.
        if user.is_superuser:
            return True

        role = user.role

        # Administrador:
        # acceso global.
        if role == UserRole.ADMINISTRATOR:
            return True

        # Comando de la Armada:
        # lectura global.
        if role == UserRole.NAVY_COMMAND:
            return request.method in SAFE_METHODS

        # -----------------------------------------------------
        # Usuarios restringidos a su unidad.
        # -----------------------------------------------------

        user_unit_id = get_user_unit_id(
            user
        )

        if not user_unit_id:
            return False

        if not obj.unit_id:
            return False

        same_unit = (
            str(user_unit_id)
            == str(obj.unit_id)
        )

        if not same_unit:
            return False

        # Comandante, Logística y Armamento
        # pueden consultar su unidad.
        if request.method in SAFE_METHODS:
            return True

        # Solo Logística y Armamento pueden
        # registrar operaciones en su unidad.
        return role in {
            UserRole.LOGISTICS_CHIEF,
            UserRole.ARMAMENT_OFFICER,
        }