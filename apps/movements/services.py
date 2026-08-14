from django.core.exceptions import ValidationError
from django.db import transaction

from apps.inventory.models import (
    AllocationType,
    SerializedMaterial,
    SerializedStatus,
)
from apps.personnel.models import Personnel

from .models import (
    SerializedMovement,
    SerializedMovementItem,
    SerializedMovementType,
)


def _normalize_ids(values):
    """
    Elimina UUID repetidos conservando el orden.
    """

    result = []
    seen = set()

    for value in values:
        value_str = str(value)

        if value_str not in seen:
            seen.add(value_str)
            result.append(value)

    return result


# ============================================================
# SALIDA DE MATERIAL DE DOTACIÓN DE UNIDAD
# ============================================================


@transaction.atomic
def create_out_movement(
    *,
    actor,
    responsible_personnel,
    unit,
    armory,
    material_ids,
    reason,
    reference_document="",
    observations="",
):
    """
    Registra la salida temporal de uno o varios
    materiales serializados de dotación de unidad.

    Ejemplos:
    - 1 pistola de dotación de unidad.
    - 20 escopetas.
    - 100 fusiles.

    Todos los materiales se procesan en una sola
    transacción: si uno falla, ninguno sale.
    """

    if not actor:
        raise ValidationError(
            {
                "created_by": (
                    "Debe existir un usuario que "
                    "registre el movimiento."
                )
            }
        )

    material_ids = _normalize_ids(
        material_ids
    )

    if not material_ids:
        raise ValidationError(
            {
                "materials": (
                    "Debe seleccionar al menos "
                    "un material."
                )
            }
        )

    # --------------------------------------------------------
    # Bloquear al responsable durante la operación
    # --------------------------------------------------------

    responsible = (
        Personnel.objects
        .select_for_update()
        .get(
            pk=responsible_personnel.pk
        )
    )

    if not responsible.is_active:
        raise ValidationError(
            {
                "responsible_personnel": (
                    "El personal responsable "
                    "se encuentra inactivo."
                )
            }
        )

    # --------------------------------------------------------
    # Bloquear todos los materiales
    # --------------------------------------------------------

    materials = list(
        SerializedMaterial.objects
        .select_for_update()
        .filter(
            pk__in=material_ids
        )
        .order_by("pk")
    )

    if len(materials) != len(material_ids):
        raise ValidationError(
            {
                "materials": (
                    "Uno o más materiales seleccionados "
                    "no existen."
                )
            }
        )

    # --------------------------------------------------------
    # Validar TODOS antes de registrar la salida
    # --------------------------------------------------------

    for material in materials:

        if not material.is_active:
            raise ValidationError(
                {
                    "materials": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"se encuentra inactivo."
                    )
                }
            )

        if (
            material.allocation_type
            != AllocationType.UNIT
        ):
            raise ValidationError(
                {
                    "materials": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"es de dotación individual y "
                        f"no puede salir mediante movimientos "
                        f"de dotación de unidad."
                    )
                }
            )

        if (
            material.status
            != SerializedStatus.AVAILABLE
        ):
            raise ValidationError(
                {
                    "materials": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no se encuentra DISPONIBLE. "
                        f"Estado actual: {material.status}."
                    )
                }
            )

        if material.unit_id != unit.id:
            raise ValidationError(
                {
                    "materials": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no pertenece a la unidad "
                        f"del movimiento."
                    )
                }
            )

        if material.armory_id != armory.id:
            raise ValidationError(
                {
                    "materials": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no pertenece a la armería "
                        f"seleccionada."
                    )
                }
            )

    # --------------------------------------------------------
    # Crear cabecera de la salida
    # --------------------------------------------------------

    movement = SerializedMovement(
        movement_type=SerializedMovementType.OUT,
        responsible_personnel=responsible,
        unit=unit,
        armory=armory,
        reason=reason,
        reference_document=reference_document,
        observations=observations,
        created_by=actor,
    )

    movement.full_clean()
    movement.save()

    # --------------------------------------------------------
    # Crear cada material de la salida
    # --------------------------------------------------------

    for material in materials:

        item = SerializedMovementItem(
            movement=movement,
            material=material,
            source_item=None,
        )

        item.full_clean()
        item.save()

        # AVAILABLE -> ISSUED
        material.status = (
            SerializedStatus.ISSUED
        )

        material.updated_by = actor

        material.full_clean()

        material.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

    return movement


# ============================================================
# RETORNO DE MATERIAL DE DOTACIÓN DE UNIDAD
# ============================================================


@transaction.atomic
def create_return_movement(
    *,
    actor,
    responsible_personnel,
    unit,
    armory,
    source_item_ids,
    reason,
    reference_document="",
    observations="",
):
    """
    Registra el retorno de materiales que
    anteriormente salieron.

    El retorno utiliza los IDs de los items
    de la salida original.

    Esto permite controlar exactamente qué
    material salió y cuál retornó.
    """

    if not actor:
        raise ValidationError(
            {
                "created_by": (
                    "Debe existir un usuario que "
                    "registre el movimiento."
                )
            }
        )

    source_item_ids = _normalize_ids(
        source_item_ids
    )

    if not source_item_ids:
        raise ValidationError(
            {
                "source_items": (
                    "Debe seleccionar al menos "
                    "un material para retornar."
                )
            }
        )

    # --------------------------------------------------------
    # Bloquear responsable
    # --------------------------------------------------------

    responsible = (
        Personnel.objects
        .select_for_update()
        .get(
            pk=responsible_personnel.pk
        )
    )

    if not responsible.is_active:
        raise ValidationError(
            {
                "responsible_personnel": (
                    "El personal responsable "
                    "se encuentra inactivo."
                )
            }
        )

    # --------------------------------------------------------
    # Bloquear registros de salida
    # --------------------------------------------------------

    source_items = list(
        SerializedMovementItem.objects
        .select_for_update()
        .filter(
            pk__in=source_item_ids
        )
        .order_by("pk")
    )

    if (
        len(source_items)
        != len(source_item_ids)
    ):
        raise ValidationError(
            {
                "source_items": (
                    "Uno o más registros de salida "
                    "no existen."
                )
            }
        )

    # --------------------------------------------------------
    # Bloquear los materiales correspondientes
    # --------------------------------------------------------

    material_ids = [
        item.material_id
        for item in source_items
    ]

    materials = list(
        SerializedMaterial.objects
        .select_for_update()
        .filter(
            pk__in=material_ids
        )
        .order_by("pk")
    )

    material_map = {
        material.id: material
        for material in materials
    }

    # --------------------------------------------------------
    # Validar todos los retornos
    # --------------------------------------------------------

    for source_item in source_items:

        source_movement = (
            source_item.movement
        )

        material = material_map.get(
            source_item.material_id
        )

        if not material:
            raise ValidationError(
                {
                    "source_items": (
                        "No se pudo localizar uno "
                        "de los materiales."
                    )
                }
            )

        if (
            source_movement.movement_type
            != SerializedMovementType.OUT
        ):
            raise ValidationError(
                {
                    "source_items": (
                        f"El registro de "
                        f"{material.institutional_code} "
                        f"no corresponde a una salida."
                    )
                }
            )

        # Debido a que source_item está bloqueado,
        # dos solicitudes simultáneas no podrán
        # retornar la misma salida correctamente.
        if source_item.return_items.exists():
            raise ValidationError(
                {
                    "source_items": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"ya fue retornado."
                    )
                }
            )

        if (
            material.allocation_type
            != AllocationType.UNIT
        ):
            raise ValidationError(
                {
                    "source_items": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no corresponde a dotación "
                        f"de unidad."
                    )
                }
            )

        if not material.is_active:
            raise ValidationError(
                {
                    "source_items": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"se encuentra inactivo."
                    )
                }
            )

        if (
            material.status
            != SerializedStatus.ISSUED
        ):
            raise ValidationError(
                {
                    "source_items": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no se encuentra en estado "
                        f"de SALIDA TEMPORAL."
                    )
                }
            )

        if material.unit_id != unit.id:
            raise ValidationError(
                {
                    "source_items": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no pertenece a la unidad "
                        f"del retorno."
                    )
                }
            )

        if material.armory_id != armory.id:
            raise ValidationError(
                {
                    "source_items": (
                        f"El material "
                        f"{material.institutional_code} "
                        f"no pertenece a la armería "
                        f"seleccionada."
                    )
                }
            )

    # --------------------------------------------------------
    # Crear cabecera del retorno
    # --------------------------------------------------------

    movement = SerializedMovement(
        movement_type=SerializedMovementType.RETURN,
        responsible_personnel=responsible,
        unit=unit,
        armory=armory,
        reason=reason,
        reference_document=reference_document,
        observations=observations,
        created_by=actor,
    )

    movement.full_clean()
    movement.save()

    # --------------------------------------------------------
    # Crear retornos
    # --------------------------------------------------------

    for source_item in source_items:

        material = material_map[
            source_item.material_id
        ]

        return_item = SerializedMovementItem(
            movement=movement,
            material=material,
            source_item=source_item,
        )

        return_item.full_clean()
        return_item.save()

        # ISSUED -> AVAILABLE
        material.status = (
            SerializedStatus.AVAILABLE
        )

        material.updated_by = actor

        material.full_clean()

        material.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

    return movement