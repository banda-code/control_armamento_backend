import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.inventory.models import SerializedStatus


class AssignmentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Dotación activa"
    RETURNED = "RETURNED", "Devuelto"


class IndividualAssignment(models.Model):
    """
    Registra la entrega individual de un material
    serializado a un miembro del personal militar.

    Ejemplos:
    - Pistola
    - Fusil
    - Rifle
    - Cuchillo bayoneta

    El cuchillo bayoneta se registra como un
    SerializedMaterial independiente.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ---------------------------------------------------------
    # Personal que recibe el material
    # ---------------------------------------------------------

    personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="individual_assignments",
        verbose_name="Personal militar",
    )

    # ---------------------------------------------------------
    # Material entregado
    # ---------------------------------------------------------

    material = models.ForeignKey(
        "inventory.SerializedMaterial",
        on_delete=models.PROTECT,
        related_name="individual_assignments",
        verbose_name="Material serializado",
    )

    # ---------------------------------------------------------
    # Datos de entrega
    # ---------------------------------------------------------

    assigned_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Fecha y hora de dotación",
    )

    assignment_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de respaldo de entrega",
    )

    assignment_observations = models.TextField(
        blank=True,
        verbose_name="Observaciones de entrega",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="individual_assignments_created",
        verbose_name="Registrado por",
    )

    # ---------------------------------------------------------
    # Estado de la dotación
    # ---------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE,
        db_index=True,
        verbose_name="Estado de la dotación",
    )

    # ---------------------------------------------------------
    # Datos de devolución
    # ---------------------------------------------------------

    returned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha y hora de devolución",
    )

    return_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de respaldo de devolución",
    )

    return_observations = models.TextField(
        blank=True,
        verbose_name="Observaciones de devolución",
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="individual_assignments_returned",
        null=True,
        blank=True,
        verbose_name="Devolución registrada por",
    )

    # ---------------------------------------------------------
    # Auditoría temporal
    # ---------------------------------------------------------

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
            "-assigned_at",
        ]

        verbose_name = "Dotación individual"
        verbose_name_plural = "Dotaciones individuales"

        constraints = [
            # Un material serializado solamente puede
            # tener una dotación activa al mismo tiempo.
            models.UniqueConstraint(
                fields=[
                    "material",
                ],
                condition=models.Q(
                    status=AssignmentStatus.ACTIVE
                ),
                name="unique_active_assignment_material",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "personnel",
                    "status",
                ],
                name="assign_person_status_idx",
            ),
            models.Index(
                fields=[
                    "material",
                    "status",
                ],
                name="assign_material_status_idx",
            ),
        ]

    def clean(self):
        errors = {}

        # -----------------------------------------------------
        # Personal
        # -----------------------------------------------------

        if self.personnel_id:
            if not self.personnel.is_active:
                errors["personnel"] = (
                    "No se puede realizar una dotación "
                    "a personal inactivo."
                )

            if not self.personnel.unit_id:
                errors["personnel"] = (
                    "El personal debe estar asociado "
                    "a una unidad."
                )

        # -----------------------------------------------------
        # Material
        # -----------------------------------------------------

        if self.material_id:
            if not self.material.is_active:
                errors["material"] = (
                    "El material seleccionado "
                    "se encuentra inactivo."
                )

            # Esta comprobación se aplica al crear
            # una nueva dotación.
            if (
                self._state.adding
                and self.material.status
                != SerializedStatus.AVAILABLE
            ):
                errors["material"] = (
                    "El material debe encontrarse "
                    "DISPONIBLE para ser asignado."
                )

        # -----------------------------------------------------
        # Personal y material deben pertenecer
        # a la misma unidad.
        # -----------------------------------------------------

        if (
            self.personnel_id
            and self.material_id
            and self.personnel.unit_id
            and self.material.unit_id
            and self.personnel.unit_id
            != self.material.unit_id
        ):
            errors["material"] = (
                "El material y el personal deben "
                "pertenecer a la misma unidad."
            )

        # -----------------------------------------------------
        # Consistencia de la devolución
        # -----------------------------------------------------

        if self.status == AssignmentStatus.ACTIVE:
            if self.returned_at:
                errors["returned_at"] = (
                    "Una dotación activa no puede tener "
                    "fecha de devolución."
                )

            if self.returned_by_id:
                errors["returned_by"] = (
                    "Una dotación activa no puede tener "
                    "usuario de devolución."
                )

        if self.status == AssignmentStatus.RETURNED:
            if not self.returned_at:
                errors["returned_at"] = (
                    "Debe registrar la fecha de devolución."
                )

            if not self.returned_by_id:
                errors["returned_by"] = (
                    "Debe registrar quién realizó "
                    "la devolución."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.personnel.full_name} - "
            f"{self.material.institutional_code}"
        )
    
class IndividualAssignmentComponent(models.Model):
    """
    Registra los componentes que se entregan
    junto con el material principal de una
    dotación individual.

    Ejemplos:
    - cargadores,
    - correas,
    - estuches,
    - kits.

    El cuchillo bayoneta NO se registra aquí.
    Se maneja como SerializedMaterial independiente.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    assignment = models.ForeignKey(
        IndividualAssignment,
        on_delete=models.CASCADE,
        related_name="assigned_components",
        verbose_name="Dotación individual",
    )

    component = models.ForeignKey(
        "inventory.SerializedMaterialComponent",
        on_delete=models.PROTECT,
        related_name="assignment_records",
        verbose_name="Componente entregado",
    )

    quantity_delivered = models.PositiveIntegerField(
        default=1,
        verbose_name="Cantidad entregada",
    )

    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones de entrega",
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
            "component__component_type__name",
        ]

        verbose_name = "Componente de dotación individual"
        verbose_name_plural = (
            "Componentes de dotaciones individuales"
        )

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    quantity_delivered__gte=1
                ),
                name="assignment_component_qty_positive",
            ),

            models.UniqueConstraint(
                fields=[
                    "assignment",
                    "component",
                ],
                name="unique_component_per_assignment",
            ),
        ]

    def clean(self):
        errors = {}

        if self.assignment_id and self.component_id:

            # -------------------------------------------------
            # El componente debe estar activo.
            # -------------------------------------------------

            if not self.component.is_active:
                errors["component"] = (
                    "El componente seleccionado "
                    "se encuentra inactivo."
                )

            # -------------------------------------------------
            # El componente debe pertenecer al mismo
            # material principal de la dotación.
            # -------------------------------------------------

            if (
                self.component.material_id
                != self.assignment.material_id
            ):
                errors["component"] = (
                    "El componente seleccionado no pertenece "
                    "al material principal de esta dotación."
                )

            # -------------------------------------------------
            # No se puede entregar una cantidad superior
            # a la registrada para el componente.
            # -------------------------------------------------

            if (
                self.quantity_delivered
                > self.component.quantity
            ):
                errors["quantity_delivered"] = (
                    "La cantidad entregada no puede ser "
                    "mayor a la cantidad registrada "
                    "para este componente."
                )

            # -------------------------------------------------
            # Si el componente tiene identificación
            # individual, solamente puede entregarse
            # una unidad.
            # -------------------------------------------------

            if (
                self.component.component_type.is_serialized
                and self.quantity_delivered != 1
            ):
                errors["quantity_delivered"] = (
                    "Un componente con identificación "
                    "individual debe entregarse con "
                    "cantidad igual a 1."
                )

        if errors:
            raise ValidationError(
                errors
            )

    def __str__(self):
        return (
            f"{self.component.component_type.name} "
            f"x {self.quantity_delivered} - "
            f"{self.assignment.material.institutional_code}"
        )