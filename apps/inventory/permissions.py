from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)

from apps.accounts.scopes import get_user_unit_id


ADMINISTRATOR = "ADMINISTRATOR"
NAVY_COMMAND = "NAVY_COMMAND"
UNIT_COMMANDER = "UNIT_COMMANDER"
LOGISTICS_CHIEF = "LOGISTICS_CHIEF"
ARMAMENT_OFFICER = "ARMAMENT_OFFICER"


READ_ROLES = {
    ADMINISTRATOR,
    NAVY_COMMAND,
    UNIT_COMMANDER,
    LOGISTICS_CHIEF,
    ARMAMENT_OFFICER,
}


UNIT_WRITE_ROLES = {
    ADMINISTRATOR,
    LOGISTICS_CHIEF,
    ARMAMENT_OFFICER,
}


def get_user_role(user):
    """
    Obtiene el rol del usuario.

    El superusuario se considera administrador.
    """

    if getattr(user, "is_superuser", False):
        return ADMINISTRATOR

    return getattr(user, "role", None)


def get_object_unit_id(obj):
    """
    Obtiene la unidad relacionada con un
    objeto del inventario.
    """

    # Materiales, lotes, armerías, etc.
    if hasattr(obj, "unit_id"):
        return obj.unit_id

    # Por ejemplo:
    # SerializedMaterialComponent -> material -> unit
    material = getattr(
        obj,
        "material",
        None,
    )

    if material is not None:
        return material.unit_id

    # Objetos relacionados con una armería.
    armory = getattr(
        obj,
        "armory",
        None,
    )

    if armory is not None:
        return armory.unit_id

    return None


def user_can_write_unit(user, unit_id):
    """
    Verifica si el usuario puede modificar
    información correspondiente a una unidad.

    La unidad del usuario se obtiene desde:

    User -> Personnel -> Unit
    """

    role = get_user_role(user)

    # El administrador tiene alcance total.
    if role == ADMINISTRATOR:
        return True

    # Estos son los únicos roles de unidad
    # autorizados para modificar inventario.
    if role not in {
        LOGISTICS_CHIEF,
        ARMAMENT_OFFICER,
    }:
        return False

    user_unit_id = get_user_unit_id(user)

    if user_unit_id is None:
        return False

    return str(user_unit_id) == str(unit_id)


class CatalogPermission(BasePermission):
    """
    Permisos para catálogos del inventario.

    Todos los roles autorizados pueden consultar.

    Solamente el administrador puede:
    - crear,
    - modificar,
    - desactivar catálogos.
    """

    message = (
        "No tiene permiso para administrar "
        "este catálogo."
    )

    def has_permission(self, request, view):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        role = get_user_role(user)

        if request.method in SAFE_METHODS:
            return role in READ_ROLES

        return role == ADMINISTRATOR


class UnitInventoryPermission(BasePermission):
    """
    Permisos para inventario por unidad.

    Administrador:
        acceso total.

    Comando de la Armada:
        consulta global.

    Comandante de Unidad:
        consulta de su propia unidad.

    Jefe de Logística:
        consulta y modificación de su unidad.

    Encargado de Armamento:
        consulta y modificación de su unidad.
    """

    message = (
        "No tiene permiso para acceder "
        "o modificar el inventario "
        "de esta unidad."
    )

    def has_permission(self, request, view):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        role = get_user_role(user)

        if role not in READ_ROLES:
            return False

        # Las consultas están permitidas.
        # El queryset posteriormente limitará
        # lo que cada usuario puede visualizar.
        if request.method in SAFE_METHODS:
            return True

        # La eliminación/desactivación queda
        # reservada al administrador.
        if request.method == "DELETE":
            return role == ADMINISTRATOR

        return role in UNIT_WRITE_ROLES

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user
        role = get_user_role(user)

        # Administrador: acceso total.
        if role == ADMINISTRATOR:
            return True

        object_unit_id = get_object_unit_id(
            obj
        )

        # Un objeto sin unidad identificable
        # no puede ser manipulado por un rol
        # restringido a unidad.
        if object_unit_id is None:
            return False

        # Comando de la Armada:
        # consulta global, sin modificación.
        if role == NAVY_COMMAND:
            return (
                request.method in SAFE_METHODS
            )

        # Obtenemos la unidad desde Personnel.
        user_unit_id = get_user_unit_id(user)

        if user_unit_id is None:
            return False

        same_unit = (
            str(user_unit_id)
            == str(object_unit_id)
        )

        if not same_unit:
            return False

        # Comandante, Logística y Armamento
        # pueden consultar su unidad.
        if request.method in SAFE_METHODS:
            return True

        # Solo Logística y Armamento pueden
        # modificar información de su unidad.
        return role in {
            LOGISTICS_CHIEF,
            ARMAMENT_OFFICER,
        }