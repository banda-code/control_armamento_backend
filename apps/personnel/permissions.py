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


class PersonnelPermission(BasePermission):
    """
    Control de acceso para registros de personal militar.

    Administrador:
        - consulta global
        - creación
        - modificación

    Comando de la Armada:
        - consulta global

    Comandante de Unidad:
        - consulta de su unidad

    Jefe de Logística:
        - consulta de su unidad

    Encargado de Armamento:
        - consulta de su unidad

    La eliminación física no se permite.
    Para retirar personal se utilizará is_active=False.
    """

    message = (
        "No tiene permiso para acceder "
        "o modificar este registro de personal."
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

        # Superusuario técnico:
        # acceso total.
        if user.is_superuser:
            return True

        role = user.role

        if role not in READ_ROLES:
            return False

        # Todos los roles autorizados
        # pueden realizar consultas.
        if request.method in SAFE_METHODS:
            return True

        # La creación y modificación
        # queda reservada al administrador.
        return role == UserRole.ADMINISTRATOR

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        # Superusuario técnico.
        if user.is_superuser:
            return True

        role = user.role

        # Administrador:
        # alcance total.
        if role == UserRole.ADMINISTRATOR:
            return True

        # Comando de la Armada:
        # lectura global.
        if role == UserRole.NAVY_COMMAND:
            return request.method in SAFE_METHODS

        # Los demás roles deben pertenecer
        # a una unidad.
        user_unit_id = get_user_unit_id(
            user
        )

        if not user_unit_id:
            return False

        # El registro Personnel también
        # debe tener unidad.
        if not obj.unit_id:
            return False

        # Solamente puede consultar personal
        # perteneciente a su propia unidad.
        same_unit = (
            str(user_unit_id)
            == str(obj.unit_id)
        )

        if not same_unit:
            return False

        return request.method in SAFE_METHODS