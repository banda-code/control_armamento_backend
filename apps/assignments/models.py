import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.inventory.models import (
    AllocationType,
    SerializedStatus,
)


# ============================================================
# ESTADOS DE DOTACIÓN
# ============================================================


class AssignmentStatus(models.TextChoices):
    ACTIVE = (
        "ACTIVE",
        "Dotación activa",
    )

    RETURNED = (
        "RETURNED",
        "Dotación finalizada",
    )


# ============================================================
# FOTOGRAFÍAS
# ============================================================


class AssignmentPhotoMoment(models.TextChoices):
    DELIVERY = (
        "DELIVERY",
        "Entrega",
    )

    RETURN = (
        "RETURN",
        "Devolución definitiva",
    )


class AssignmentPhotoType(models.TextChoices):
    GENERAL = (
        "GENERAL",
        "Vista general",
    )

    SERIAL = (
        "SERIAL",
        "Número de identificación o serie",
    )

    LEFT_SIDE = (
        "LEFT_SIDE",
        "Lado izquierdo",
    )

    RIGHT_SIDE = (
        "RIGHT_SIDE",
        "Lado derecho",
    )

    COMPONENTS = (
        "COMPONENTS",
        "Componentes",
    )

    OTHER = (
        "OTHER",
        "Otra fotografía",
    )


# ============================================================
# CUSTODIA FÍSICA
# ============================================================


class AssignmentCustodyMovementType(models.TextChoices):
    DELIVERY = (
        "DELIVERY",
        "Entrega al personal",
    )

    RECEIPT = (
        "RECEIPT",
        "Recepción en pañol",
    )


class AssignmentCustodyState(models.TextChoices):
    ARMORY = (
        "ARMORY",
        "En pañol",
    )

    PERSONNEL = (
        "PERSONNEL",
        "En poder del personal",
    )


# ============================================================
# DOTACIÓN INDIVIDUAL
# ============================================================


class IndividualAssignment(models.Model):
    """
    Registra la dotación administrativa de un material
    serializado a un miembro del personal militar.

    Esta relación es diferente de la custodia física.

    Ejemplo:

        Dotación:
            Personal A <-> Pistola 001

        Custodia:
            En pañol
            -> Entrega al personal
            -> Recepción en pañol
            -> Entrega nuevamente
            -> Recepción nuevamente

    Mientras la dotación permanezca ACTIVE, el material
    continúa administrativamente asignado al personal,
    independientemente de si físicamente está en el
    pañol o en poder del personal.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="individual_assignments",
        verbose_name="Personal militar",
    )

    material = models.ForeignKey(
        "inventory.SerializedMaterial",
        on_delete=models.PROTECT,
        related_name="individual_assignments",
        verbose_name="Material serializado",
    )

    assigned_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Fecha y hora de dotación",
    )

    assignment_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de respaldo de dotación",
    )

    assignment_observations = models.TextField(
        blank=True,
        verbose_name="Observaciones de dotación",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="individual_assignments_created",
        verbose_name="Registrado por",
    )

    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE,
        db_index=True,
        verbose_name="Estado de la dotación",
    )

    # --------------------------------------------------------
    # Cierre definitivo de dotación
    # --------------------------------------------------------

    returned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha y hora de cierre",
    )

    return_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de cierre de dotación",
    )

    return_observations = models.TextField(
        blank=True,
        verbose_name="Observaciones de cierre",
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="individual_assignments_returned",
        null=True,
        blank=True,
        verbose_name="Cierre registrado por",
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
            "-assigned_at",
        ]

        verbose_name = "Dotación individual"
        verbose_name_plural = (
            "Dotaciones individuales"
        )

        constraints = [
            # Un material puede conservar historial de
            # dotaciones finalizadas, pero solamente puede
            # tener UNA dotación ACTIVA al mismo tiempo.
            models.UniqueConstraint(
                fields=[
                    "material",
                ],
                condition=models.Q(
                    status=AssignmentStatus.ACTIVE
                ),
                name=(
                    "unique_active_assignment_material"
                ),
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

        # ----------------------------------------------------
        # Personal
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Material
        # ----------------------------------------------------

        if self.material_id:
            if not self.material.is_active:
                errors["material"] = (
                    "El material seleccionado "
                    "se encuentra inactivo."
                )

            if (
                self.material.allocation_type
                != AllocationType.INDIVIDUAL
            ):
                errors["material"] = (
                    "Solamente puede registrarse como "
                    "dotación individual un material "
                    "clasificado como INDIVIDUAL."
                )

            # Solo al crear una nueva dotación.
            if (
                self._state.adding
                and self.material.status
                != SerializedStatus.AVAILABLE
            ):
                errors["material"] = (
                    "El material debe encontrarse "
                    "DISPONIBLE para iniciar una dotación."
                )

        # ----------------------------------------------------
        # Misma unidad
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Consistencia del estado
        # ----------------------------------------------------

        if (
            self.status
            == AssignmentStatus.ACTIVE
        ):
            if self.returned_at:
                errors["returned_at"] = (
                    "Una dotación activa no puede tener "
                    "fecha de cierre."
                )

            if self.returned_by_id:
                errors["returned_by"] = (
                    "Una dotación activa no puede tener "
                    "usuario de cierre."
                )

        elif (
            self.status
            == AssignmentStatus.RETURNED
        ):
            if not self.returned_at:
                errors["returned_at"] = (
                    "Debe registrar la fecha de cierre "
                    "de la dotación."
                )

            if not self.returned_by_id:
                errors["returned_by"] = (
                    "Debe registrar quién realizó "
                    "el cierre de la dotación."
                )

        if errors:
            raise ValidationError(
                errors
            )

    # ========================================================
    # ESTADO ACTUAL DE CUSTODIA
    # ========================================================

    def get_current_custody_state(self):
        """
        Determina quién posee físicamente el material.

        Si la dotación está finalizada:
            ARMORY

        Si todavía no existen movimientos:
            ARMORY

        Último movimiento DELIVERY:
            PERSONNEL

        Último movimiento RECEIPT:
            ARMORY
        """

        if (
            self.status
            == AssignmentStatus.RETURNED
        ):
            return AssignmentCustodyState.ARMORY

        latest_item = (
            self.custody_items
            .select_related(
                "movement",
            )
            .order_by(
                "-movement__movement_at",
                "-created_at",
            )
            .first()
        )

        if not latest_item:
            return AssignmentCustodyState.ARMORY

        if (
            latest_item
            .movement
            .movement_type
            == AssignmentCustodyMovementType.DELIVERY
        ):
            return AssignmentCustodyState.PERSONNEL

        return AssignmentCustodyState.ARMORY

    def __str__(self):
        return (
            f"{self.personnel.full_name} - "
            f"{self.material.institutional_code}"
        )


# ============================================================
# COMPONENTES DE DOTACIÓN
# ============================================================


class IndividualAssignmentComponent(models.Model):
    """
    Componentes entregados junto con el material
    principal.

    Ejemplos:
    - cargadores,
    - correas,
    - estuches,
    - kits.

    El cuchillo bayoneta NO se registra aquí si posee
    control individual; debe manejarse como un
    SerializedMaterial independiente.
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

    quantity_delivered = (
        models.PositiveIntegerField(
            default=1,
            verbose_name="Cantidad entregada",
        )
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

        verbose_name = (
            "Componente de dotación individual"
        )

        verbose_name_plural = (
            "Componentes de dotaciones individuales"
        )

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    quantity_delivered__gte=1
                ),
                name=(
                    "assignment_component_qty_positive"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "assignment",
                    "component",
                ],
                name=(
                    "unique_component_per_assignment"
                ),
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.assignment_id
            and self.component_id
        ):
            # ------------------------------------------------
            # Componente activo
            # ------------------------------------------------

            if not self.component.is_active:
                errors["component"] = (
                    "El componente seleccionado "
                    "se encuentra inactivo."
                )

            # ------------------------------------------------
            # Debe pertenecer al material principal
            # ------------------------------------------------

            if (
                self.component.material_id
                != self.assignment.material_id
            ):
                errors["component"] = (
                    "El componente seleccionado no "
                    "pertenece al material principal "
                    "de esta dotación."
                )

            # ------------------------------------------------
            # Cantidad válida
            # ------------------------------------------------

            if (
                self.quantity_delivered
                > self.component.quantity
            ):
                errors[
                    "quantity_delivered"
                ] = (
                    "La cantidad entregada no puede "
                    "ser mayor a la cantidad registrada "
                    "para este componente."
                )

            # ------------------------------------------------
            # Componente serializado
            # ------------------------------------------------

            if (
                self.component
                .component_type
                .is_serialized
                and self.quantity_delivered != 1
            ):
                errors[
                    "quantity_delivered"
                ] = (
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


# ============================================================
# FOTOGRAFÍAS DE DOTACIÓN
# ============================================================


class IndividualAssignmentPhoto(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    assignment = models.ForeignKey(
        IndividualAssignment,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Dotación individual",
    )

    moment = models.CharField(
        max_length=20,
        choices=AssignmentPhotoMoment.choices,
        verbose_name="Momento de la fotografía",
    )

    photo_type = models.CharField(
        max_length=20,
        choices=AssignmentPhotoType.choices,
        default=AssignmentPhotoType.GENERAL,
        verbose_name="Tipo de fotografía",
    )

    photo = models.ImageField(
        upload_to=(
            "assignments/photos/%Y/%m/"
        ),
        verbose_name="Fotografía",
    )

    description = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Descripción",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name=(
            "individual_assignment_photos_uploaded"
        ),
        verbose_name="Registrado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = (
            "Fotografía de dotación individual"
        )

        verbose_name_plural = (
            "Fotografías de dotaciones individuales"
        )

        ordering = [
            "moment",
            "photo_type",
            "created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "assignment",
                    "moment",
                ],
                name="assign_photo_moment_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.assignment.material.institutional_code} - "
            f"{self.get_moment_display()} - "
            f"{self.get_photo_type_display()}"
        )


# ============================================================
# MOVIMIENTOS DE CUSTODIA
# ============================================================


class IndividualAssignmentCustodyMovement(
    models.Model
):
    """
    Cabecera de una operación física de custodia.

    Una sola operación puede contener varios materiales
    pertenecientes al mismo personal.

    Ejemplo:

        ENTREGA AL PERSONAL
        - Pistola
        - Cuchillo bayoneta

    o:

        RECEPCIÓN EN PAÑOL
        - Pistola
        - Cuchillo bayoneta
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    movement_type = models.CharField(
        max_length=20,
        choices=(
            AssignmentCustodyMovementType.choices
        ),
        db_index=True,
        verbose_name="Tipo de movimiento",
    )

    personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name=(
            "individual_custody_movements"
        ),
        verbose_name="Personal militar",
    )

    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.PROTECT,
        related_name=(
            "individual_custody_movements"
        ),
        verbose_name="Unidad",
    )

    armory = models.ForeignKey(
        "inventory.Armory",
        on_delete=models.PROTECT,
        related_name=(
            "individual_custody_movements"
        ),
        verbose_name="Armería / Pañol",
    )

    movement_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Fecha y hora del movimiento",
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
        related_name=(
            "individual_custody_movements_created"
        ),
        verbose_name="Registrado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-movement_at",
            "-created_at",
        ]

        verbose_name = (
            "Movimiento de custodia "
            "de dotación individual"
        )

        verbose_name_plural = (
            "Movimientos de custodia "
            "de dotaciones individuales"
        )

        indexes = [
            models.Index(
                fields=[
                    "personnel",
                    "movement_type",
                ],
                name=(
                    "assign_cust_person_type_idx"
                ),
            ),

            models.Index(
                fields=[
                    "unit",
                    "movement_at",
                ],
                name=(
                    "assign_cust_unit_date_idx"
                ),
            ),
        ]

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # Personal
        # ----------------------------------------------------

        if self.personnel_id:
            if not self.personnel.is_active:
                errors["personnel"] = (
                    "No se puede registrar un movimiento "
                    "de custodia para personal inactivo."
                )

        # ----------------------------------------------------
        # Personal y unidad
        # ----------------------------------------------------

        if (
            self.personnel_id
            and self.unit_id
            and self.personnel.unit_id
            and self.personnel.unit_id
            != self.unit_id
        ):
            errors["unit"] = (
                "El personal no pertenece a la unidad "
                "del movimiento."
            )

        # ----------------------------------------------------
        # Pañol y unidad
        # ----------------------------------------------------

        if (
            self.armory_id
            and self.unit_id
            and self.armory.unit_id
            != self.unit_id
        ):
            errors["armory"] = (
                "El pañol seleccionado no pertenece "
                "a la unidad del movimiento."
            )

        if errors:
            raise ValidationError(
                errors
            )

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} - "
            f"{self.personnel.full_name}"
        )


# ============================================================
# MATERIALES DE CADA MOVIMIENTO DE CUSTODIA
# ============================================================


class IndividualAssignmentCustodyItem(
    models.Model
):
    """
    Relaciona un movimiento de custodia con las
    dotaciones individuales incluidas en él.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    movement = models.ForeignKey(
        IndividualAssignmentCustodyMovement,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Movimiento",
    )

    assignment = models.ForeignKey(
        IndividualAssignment,
        on_delete=models.PROTECT,
        related_name="custody_items",
        verbose_name="Dotación individual",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = (
            "Material de movimiento de custodia"
        )

        verbose_name_plural = (
            "Materiales de movimientos de custodia"
        )

        constraints = [
            # La misma dotación no puede aparecer
            # dos veces dentro de una misma operación.
            models.UniqueConstraint(
                fields=[
                    "movement",
                    "assignment",
                ],
                name=(
                    "unique_assignment_per_custody_movement"
                ),
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.assignment_id
            and self.movement_id
        ):
            assignment = self.assignment
            movement = self.movement
            material = assignment.material

            # ------------------------------------------------
            # Dotación activa
            # ------------------------------------------------

            if (
                assignment.status
                != AssignmentStatus.ACTIVE
            ):
                errors["assignment"] = (
                    "La dotación individual debe "
                    "encontrarse ACTIVA."
                )

            # ------------------------------------------------
            # Mismo personal
            # ------------------------------------------------

            if (
                assignment.personnel_id
                != movement.personnel_id
            ):
                errors["assignment"] = (
                    "La dotación no pertenece al "
                    "personal del movimiento."
                )

            # ------------------------------------------------
            # Misma unidad
            # ------------------------------------------------

            if (
                material.unit_id
                != movement.unit_id
            ):
                errors["assignment"] = (
                    "El material no pertenece a la "
                    "unidad del movimiento."
                )

            # ------------------------------------------------
            # Mismo pañol
            # ------------------------------------------------

            if (
                material.armory_id
                != movement.armory_id
            ):
                errors["assignment"] = (
                    "El material no pertenece al "
                    "pañol seleccionado."
                )

        if errors:
            raise ValidationError(
                errors
            )

    def __str__(self):
        return (
            f"{self.assignment.material.institutional_code} - "
            f"{self.movement.get_movement_type_display()}"
        )