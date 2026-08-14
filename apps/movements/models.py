import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.inventory.models import (
    AllocationType,
)


class SerializedMovementType(models.TextChoices):
    OUT = (
        "OUT",
        "Salida",
    )

    RETURN = (
        "RETURN",
        "Retorno",
    )


class SerializedMovement(models.Model):
    """
    Registra la salida o retorno físico de uno
    o varios materiales serializados de dotación
    de unidad.

    No modifica ninguna dotación individual.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    movement_type = models.CharField(
        max_length=20,
        choices=SerializedMovementType.choices,
        db_index=True,
        verbose_name="Tipo de movimiento",
    )

    movement_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Fecha y hora del movimiento",
    )

    responsible_personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="serialized_movements_responsible",
        verbose_name="Personal responsable",
    )

    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.PROTECT,
        related_name="serialized_material_movements",
        verbose_name="Unidad",
    )

    armory = models.ForeignKey(
        "inventory.Armory",
        on_delete=models.PROTECT,
        related_name="serialized_material_movements",
        verbose_name="Armería o depósito",
    )

    reason = models.CharField(
        max_length=250,
        verbose_name="Motivo",
    )

    reference_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de respaldo",
    )

    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="serialized_movements_created",
        verbose_name="Registrado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación",
    )

    class Meta:
        ordering = [
            "-movement_at",
        ]

        verbose_name = (
            "Movimiento de material serializado"
        )

        verbose_name_plural = (
            "Movimientos de materiales serializados"
        )

        indexes = [
            models.Index(
                fields=[
                    "unit",
                    "movement_type",
                ],
                name="sermov_unit_type_idx",
            ),
            models.Index(
                fields=[
                    "responsible_personnel",
                    "movement_at",
                ],
                name="sermov_person_date_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if self.responsible_personnel_id:

            if not self.responsible_personnel.is_active:
                errors["responsible_personnel"] = (
                    "El personal responsable "
                    "se encuentra inactivo."
                )

            if not self.responsible_personnel.unit_id:
                errors["responsible_personnel"] = (
                    "El personal responsable debe "
                    "estar asociado a una unidad."
                )

            elif (
                self.unit_id
                and self.responsible_personnel.unit_id
                != self.unit_id
            ):
                errors["responsible_personnel"] = (
                    "El personal responsable debe "
                    "pertenecer a la unidad del movimiento."
                )

        if (
            self.armory_id
            and self.unit_id
            and self.armory.unit_id
            != self.unit_id
        ):
            errors["armory"] = (
                "La armería seleccionada no pertenece "
                "a la unidad del movimiento."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} - "
            f"{self.responsible_personnel.full_name} - "
            f"{self.movement_at:%d/%m/%Y %H:%M}"
        )


class SerializedMovementItem(models.Model):
    """
    Material serializado incluido en un movimiento.

    Un movimiento puede tener 1, 10, 100 o más
    materiales, pero cada uno conserva su UUID,
    código institucional y número de identificación.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    movement = models.ForeignKey(
        SerializedMovement,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="Movimiento",
    )

    material = models.ForeignKey(
        "inventory.SerializedMaterial",
        on_delete=models.PROTECT,
        related_name="serialized_movement_items",
        verbose_name="Material serializado",
    )

    # Para un RETORNO indicará exactamente
    # de qué salida proviene este material.
    source_item = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="return_items",
        null=True,
        blank=True,
        verbose_name="Registro de salida original",
    )

    observations = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Observaciones",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        ordering = [
            "material__institutional_code",
        ]

        verbose_name = (
            "Material de movimiento serializado"
        )

        verbose_name_plural = (
            "Materiales de movimientos serializados"
        )

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "movement",
                    "material",
                ],
                name="unique_material_per_sermovement",
            ),

            # Una salida individual solo puede
            # tener un retorno.
            models.UniqueConstraint(
                fields=[
                    "source_item",
                ],
                condition=models.Q(
                    source_item__isnull=False,
                ),
                name="unique_return_per_source_item",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.material_id:
            return

        material = self.material

        # -----------------------------------------------------
        # Solo dotación de UNIDAD.
        # -----------------------------------------------------

        if (
            material.allocation_type
            != AllocationType.UNIT
        ):
            errors["material"] = (
                "Los movimientos de unidad solamente "
                "pueden registrar materiales con "
                "dotación de unidad."
            )

        if not material.is_active:
            errors["material"] = (
                "El material seleccionado "
                "se encuentra inactivo."
            )

        if self.movement_id:

            if (
                material.unit_id
                != self.movement.unit_id
            ):
                errors["material"] = (
                    "El material no pertenece "
                    "a la unidad del movimiento."
                )

            if (
                material.armory_id
                != self.movement.armory_id
            ):
                errors["material"] = (
                    "El material no pertenece "
                    "a la armería seleccionada."
                )

            # ---------------------------------------------
            # SALIDA
            # ---------------------------------------------

            if (
                self.movement.movement_type
                == SerializedMovementType.OUT
            ):
                if self.source_item_id:
                    errors["source_item"] = (
                        "Una salida no puede tener "
                        "un registro de salida original."
                    )

            # ---------------------------------------------
            # RETORNO
            # ---------------------------------------------

            if (
                self.movement.movement_type
                == SerializedMovementType.RETURN
            ):
                if not self.source_item_id:
                    errors["source_item"] = (
                        "Debe indicar la salida original "
                        "del material que está retornando."
                    )

                elif (
                    self.source_item.material_id
                    != material.id
                ):
                    errors["source_item"] = (
                        "El material retornado no coincide "
                        "con el material de la salida original."
                    )

                elif (
                    self.source_item.movement.movement_type
                    != SerializedMovementType.OUT
                ):
                    errors["source_item"] = (
                        "El registro de origen debe "
                        "corresponder a una salida."
                    )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.material.institutional_code} - "
            f"{self.movement.get_movement_type_display()}"
        )