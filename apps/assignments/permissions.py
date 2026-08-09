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


class IndividualAssignmentPermission(BasePermission):
    """
    Permisos para dotaciones individuales.

    Administrador:
        - consulta global
        - registra entregas
        - registra devoluciones

    Comando de la Armada:
        - consulta global

    Comandante de Unidad:
        - consulta de su unidad

    Jefe de Logística:
        - consulta de su unidad
        - registra entregas
        - registra devoluciones

    Encargado de Armamento:
        - consulta de su unidad
        - registra entregas
        - registra devoluciones

    No se permite eliminación física.
    """

    message = (
        "No tiene permiso para acceder "
        "o modificar esta dotación."
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

        # Consultas.
        if request.method in SAFE_METHODS:
            return True

        # No permitimos DELETE.
        if request.method == "DELETE":
            return False

        # Creación, devolución y demás
        # operaciones de escritura.
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
        # alcance total.
        if role == UserRole.ADMINISTRATOR:
            return True

        # Comando de la Armada:
        # solamente lectura global.
        if role == UserRole.NAVY_COMMAND:
            return request.method in SAFE_METHODS

        # -----------------------------------------------------
        # Usuarios restringidos a su unidad
        # -----------------------------------------------------

        user_unit_id = get_user_unit_id(
            user
        )

        if not user_unit_id:
            return False

        # La unidad de la dotación se obtiene
        # del material serializado.
        assignment_unit_id = (
            obj.material.unit_id
            if obj.material_id
            else None
        )

        if not assignment_unit_id:
            return False

        same_unit = (
            str(user_unit_id)
            == str(assignment_unit_id)
        )

        if not same_unit:
            return False

        # Comandante, Logística y Armamento
        # pueden consultar su propia unidad.
        if request.method in SAFE_METHODS:
            return True

        # Solamente Logística y Armamento
        # pueden registrar operaciones.
        return role in {
            UserRole.LOGISTICS_CHIEF,
            UserRole.ARMAMENT_OFFICER,
        }