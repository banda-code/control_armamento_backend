def get_user_personnel(user):
    """
    Devuelve el registro Personnel asociado
    a una cuenta de usuario.
    """

    if not user:
        return None

    return getattr(
        user,
        "personnel",
        None,
    )


def get_user_unit_id(user):
    """
    Obtiene el identificador de la unidad
    desde:

    User -> Personnel -> Unit
    """

    if not user:
        return None

    personnel = get_user_personnel(
        user
    )

    if (
        personnel
        and personnel.unit_id
    ):
        return personnel.unit_id

    return None


def get_user_unit(user):
    """
    Obtiene la unidad del usuario desde:

    User -> Personnel -> Unit
    """

    if not user:
        return None

    personnel = get_user_personnel(
        user
    )

    if (
        personnel
        and personnel.unit_id
    ):
        return personnel.unit

    return None


def scope_queryset_by_unit(
    queryset,
    user,
    unit_field="unit",
):
    """
    Limita un queryset según el alcance
    institucional del usuario.

    Usuarios con alcance global:
        pueden consultar todas las unidades.

    Usuarios de unidad:
        solamente pueden consultar su unidad.
    """

    if (
        not user
        or not user.is_authenticated
    ):
        return queryset.none()

    if user.has_global_scope:
        return queryset

    unit_id = get_user_unit_id(
        user
    )

    if not unit_id:
        return queryset.none()

    return queryset.filter(
        **{
            f"{unit_field}_id": unit_id
        }
    )