from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.scopes import get_user_unit_id
from apps.inventory.models import SerializedStatus

from .models import (
    AssignmentCustodyMovementType,
    AssignmentCustodyState,
    AssignmentStatus,
    IndividualAssignment,
    IndividualAssignmentCustodyItem,
    IndividualAssignmentCustodyMovement,
)


@transaction.atomic
def create_custody_movement(
    *,
    actor,
    assignment_ids,
    movement_type,
    reason,
    reference_document="",
    observations="",
):
    """
    Registra una entrega o recepción física de
    uno o varios materiales de dotación individual.

    No modifica la dotación administrativa.
    No modifica ASSIGNED del material.
    """

    assignment_ids = list(
        dict.fromkeys(
            str(value)
            for value in assignment_ids
        )
    )

    if not assignment_ids:
        raise ValidationError(
            {
                "assignments": (
                    "Debe seleccionar al menos "
                    "una dotación individual."
                )
            }
        )

    assignments = list(
        IndividualAssignment.objects
        .select_for_update()
        .select_related(
            "personnel",
            "material",
            "material__unit",
            "material__armory",
        )
        .filter(
            id__in=assignment_ids,
        )
        .order_by(
            "id",
        )
    )

    if len(assignments) != len(assignment_ids):
        raise ValidationError(
            {
                "assignments": (
                    "Una o más dotaciones "
                    "seleccionadas no existen."
                )
            }
        )

    first = assignments[0]

    personnel = first.personnel
    unit = first.material.unit
    armory = first.material.armory

    # ========================================================
    # ALCANCE DEL USUARIO
    # ========================================================

    if not actor.has_global_scope:
        user_unit_id = get_user_unit_id(
            actor
        )

        if not user_unit_id:
            raise ValidationError(
                {
                    "assignments": (
                        "El usuario no tiene una unidad "
                        "institucional asociada."
                    )
                }
            )

        if str(user_unit_id) != str(unit.id):
            raise ValidationError(
                {
                    "assignments": (
                        "No puede registrar movimientos "
                        "para otra unidad."
                    )
                }
            )

    # ========================================================
    # VALIDACIONES
    # ========================================================

    for assignment in assignments:

        if (
            assignment.status
            != AssignmentStatus.ACTIVE
        ):
            raise ValidationError(
                {
                    "assignments": (
                        f"La dotación del material "
                        f"{assignment.material.institutional_code} "
                        f"no se encuentra ACTIVA."
                    )
                }
            )

        if not assignment.material.is_active:
            raise ValidationError(
                {
                    "assignments": (
                        f"El material "
                        f"{assignment.material.institutional_code} "
                        f"se encuentra inactivo."
                    )
                }
            )

        if (
            assignment.material.status
            != SerializedStatus.ASSIGNED
        ):
            raise ValidationError(
                {
                    "assignments": (
                        f"El material "
                        f"{assignment.material.institutional_code} "
                        f"no se encuentra en estado ASSIGNED."
                    )
                }
            )

        # Todos deben pertenecer al mismo personal.
        if (
            assignment.personnel_id
            != personnel.id
        ):
            raise ValidationError(
                {
                    "assignments": (
                        "Todos los materiales de una misma "
                        "operación deben pertenecer al mismo "
                        "personal."
                    )
                }
            )

        # Todos deben pertenecer a la misma unidad.
        if (
            assignment.material.unit_id
            != unit.id
        ):
            raise ValidationError(
                {
                    "assignments": (
                        "Todos los materiales deben pertenecer "
                        "a la misma unidad."
                    )
                }
            )

        # Todos deben estar registrados en el mismo pañol.
        if (
            assignment.material.armory_id
            != armory.id
        ):
            raise ValidationError(
                {
                    "assignments": (
                        "Todos los materiales deben pertenecer "
                        "al mismo pañol."
                    )
                }
            )

        current_state = (
            assignment.get_current_custody_state()
        )

        # ----------------------------------------------------
        # ENTREGA DEL PAÑOL AL PERSONAL
        # ----------------------------------------------------

        if (
            movement_type
            == AssignmentCustodyMovementType.DELIVERY
        ):
            if (
                current_state
                != AssignmentCustodyState.ARMORY
            ):
                raise ValidationError(
                    {
                        "assignments": (
                            f"El material "
                            f"{assignment.material.institutional_code} "
                            f"ya se encuentra en poder del personal."
                        )
                    }
                )

        # ----------------------------------------------------
        # RECEPCIÓN DEL PERSONAL AL PAÑOL
        # ----------------------------------------------------

        elif (
            movement_type
            == AssignmentCustodyMovementType.RECEIPT
        ):
            if (
                current_state
                != AssignmentCustodyState.PERSONNEL
            ):
                raise ValidationError(
                    {
                        "assignments": (
                            f"El material "
                            f"{assignment.material.institutional_code} "
                            f"ya se encuentra físicamente "
                            f"en el pañol."
                        )
                    }
                )

        else:
            raise ValidationError(
                {
                    "movement_type": (
                        "Tipo de movimiento de custodia inválido."
                    )
                }
            )

    # ========================================================
    # CREAR CABECERA
    # ========================================================

    movement = IndividualAssignmentCustodyMovement(
        movement_type=movement_type,
        personnel=personnel,
        unit=unit,
        armory=armory,
        reason=reason,
        reference_document=reference_document,
        observations=observations,
        created_by=actor,
    )

    movement.full_clean()
    movement.save()

    # ========================================================
    # CREAR MATERIALES
    # ========================================================

    for assignment in assignments:
        item = IndividualAssignmentCustodyItem(
            movement=movement,
            assignment=assignment,
        )

        item.full_clean()
        item.save()

    return movement