import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualización",
    )

    class Meta:
        abstract = True


class ControlMethod(models.TextChoices):
    SERIALIZED = "SERIALIZED", "Control individual o serializado"
    QUANTITY = "QUANTITY", "Control por cantidad o lote"


class MaterialCategory(TimeStampedModel):
    """
    Categorías dinámicas:
    ARMAMENTO, ARMA BLANCA, CLASE V, EXPLOSIVOS,
    AGENTES QUÍMICOS, EQUIPO DE PROTECCIÓN, etc.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=120,
        unique=True,
        verbose_name="Categoría",
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Código",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Categoría de material"
        verbose_name_plural = "Categorías de material"

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MaterialType(TimeStampedModel):
    """
    Ejemplos:
    FUSIL, PISTOLA, CUCHILLO BAYONETA, MUNICIÓN,
    DINAMITA, CASCO, CHALECO, MÁSCARA ANTIGÁS.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    category = models.ForeignKey(
        MaterialCategory,
        on_delete=models.PROTECT,
        related_name="material_types",
        verbose_name="Categoría",
    )
    name = models.CharField(
        max_length=120,
        verbose_name="Tipo de material",
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Código",
    )
    control_method = models.CharField(
        max_length=20,
        choices=ControlMethod.choices,
        verbose_name="Método de control",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["category__name", "name"]
        verbose_name = "Tipo de material"
        verbose_name_plural = "Tipos de material"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_type_name_category",
            )
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Manufacturer(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=120,
        unique=True,
        verbose_name="Marca o fabricante",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Marca o fabricante"
        verbose_name_plural = "Marcas o fabricantes"

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Country(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="País o industria",
    )
    code = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="Código",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "País o industria"
        verbose_name_plural = "Países o industrias"

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Caliber(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=60,
        unique=True,
        verbose_name="Calibre",
    )
    description = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Descripción",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Calibre"
        verbose_name_plural = "Calibres"

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UnitOfMeasure(TimeStampedModel):
    """
    Ejemplos:
    UNIDAD, CARTUCHO, CAJA, METRO, KILOGRAMO, LITRO.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=60,
        unique=True,
        verbose_name="Unidad de medida",
    )
    symbol = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Símbolo",
    )
    allows_decimals = models.BooleanField(
        default=False,
        verbose_name="Permite cantidades decimales",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Unidad de medida"
        verbose_name_plural = "Unidades de medida"

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.symbol = self.symbol.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class MaterialSpecification(TimeStampedModel):
    """
    Ejemplos:
    - PISTOLA / NP22 / NORINCO / 9 MM / CHINA
    - CUCHILLO BAYONETA / S/M / CHINA
    - MUNICIÓN / CARTUCHO 5.56 X 45 MM
    - CASCO / CASCO BALÍSTICO NIVEL IIIA
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    material_type = models.ForeignKey(
        MaterialType,
        on_delete=models.PROTECT,
        related_name="specifications",
        verbose_name="Tipo de material",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Modelo o especificación",
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name="material_specifications",
        null=True,
        blank=True,
        verbose_name="Marca o fabricante",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="material_specifications",
        null=True,
        blank=True,
        verbose_name="País o industria",
    )
    caliber = models.ForeignKey(
        Caliber,
        on_delete=models.PROTECT,
        related_name="material_specifications",
        null=True,
        blank=True,
        verbose_name="Calibre",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción técnica",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["material_type__name", "name"]
        verbose_name = "Modelo o especificación"
        verbose_name_plural = "Modelos o especificaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["material_type", "name"],
                name="unique_material_spec",
            )
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.material_type.name} - {self.name}"


class Armory(TimeStampedModel):
    """
    Representa una armería, almacén o depósito
    perteneciente a una unidad militar.

    Ejemplos:
    - Armería principal
    - Depósito de Clase V
    - Depósito de explosivos
    - Almacén de equipos de protección
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.PROTECT,
        related_name="armories",
        verbose_name="Unidad",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Armería o depósito",
    )
    code = models.CharField(
        max_length=30,
        verbose_name="Código",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción o ubicación",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["unit__name", "name"]
        verbose_name = "Armería o depósito"
        verbose_name_plural = "Armerías o depósitos"
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "code"],
                name="unique_armory_code_unit",
            ),
            models.UniqueConstraint(
                fields=["unit", "name"],
                name="unique_armory_name_unit",
            ),
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.unit.name}"


class SerializedStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Disponible"
    ASSIGNED = "ASSIGNED", "Asignado"
    MAINTENANCE = "MAINTENANCE", "En mantenimiento"
    OBSERVED = "OBSERVED", "Observado"
    TRANSFER = "TRANSFER", "En transferencia"
    MISSING = "MISSING", "Extraviado"
    DISCHARGED = "DISCHARGED", "Dado de baja"


class PhysicalCondition(models.TextChoices):
    GOOD = "GOOD", "Bueno"
    REGULAR = "REGULAR", "Regular"
    DAMAGED = "DAMAGED", "Dañado"
    UNVERIFIED = "UNVERIFIED", "No verificado"


class SerializedMaterial(TimeStampedModel):
    """
    Cada elemento tiene identificación propia.
    Ejemplos: fusil, pistola, escopeta, rifle,
    cuchillo bayoneta o casco numerado.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    institutional_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Código institucional",
    )
    identification_number = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Número de serie o identificación",
    )
    specification = models.ForeignKey(
        MaterialSpecification,
        on_delete=models.PROTECT,
        related_name="serialized_materials",
        verbose_name="Modelo o especificación",
    )
    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.PROTECT,
        related_name="serialized_materials",
        verbose_name="Unidad responsable",
    )
    armory = models.ForeignKey(
        Armory,
        on_delete=models.PROTECT,
        related_name="serialized_materials",
        verbose_name="Armería o depósito actual",
    )
    status = models.CharField(
        max_length=30,
        choices=SerializedStatus.choices,
        default=SerializedStatus.AVAILABLE,
        db_index=True,
        verbose_name="Estado administrativo",
    )
    physical_condition = models.CharField(
        max_length=30,
        choices=PhysicalCondition.choices,
        default=PhysicalCondition.UNVERIFIED,
        verbose_name="Estado físico",
    )
    manufacturing_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Año de fabricación",
    )
    acquisition_source = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Procedencia o forma de adquisición",
    )
    registration_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de alta o registro",
    )
    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Registro activo",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_serialized_materials",
        null=True,
        blank=True,
        verbose_name="Registrado por",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_serialized_materials",
        null=True,
        blank=True,
        verbose_name="Última modificación por",
    )

    class Meta:
        ordering = ["institutional_code"]
        verbose_name = "Material individual o serializado"
        verbose_name_plural = "Materiales individuales o serializados"
        constraints = [
            models.UniqueConstraint(
                fields=["specification", "identification_number"],
                name="unique_serial_per_spec",
            )
        ]
        indexes = [
            models.Index(
                fields=["unit", "status"],
                name="serialized_unit_status_idx",
            ),
            models.Index(
                fields=["armory", "status"],
                name="serial_armory_status_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.specification_id
            and self.specification.material_type.control_method
            != ControlMethod.SERIALIZED
        ):
            errors["specification"] = (
                "El tipo seleccionado no está configurado "
                "para control individual o serializado."
            )

        if (
            self.armory_id
            and self.unit_id
            and self.armory.unit_id != self.unit_id
        ):
            errors["armory"] = (
                "La armería o depósito no pertenece "
                "a la unidad responsable."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.institutional_code = (
            self.institutional_code.strip().upper()
        )
        self.identification_number = (
            self.identification_number.strip().upper()
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.institutional_code} - "
            f"{self.specification.material_type.name} - "
            f"{self.identification_number}"
        )


class StockMaterial(TimeStampedModel):
    """
    Define materiales administrados por cantidad.
    Ejemplos: munición, explosivos, agentes químicos,
    cascos sin numeración individual.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    internal_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Código interno",
    )
    specification = models.ForeignKey(
        MaterialSpecification,
        on_delete=models.PROTECT,
        related_name="stock_materials",
        verbose_name="Modelo o especificación",
    )
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name="stock_materials",
        verbose_name="Unidad de medida",
    )
    minimum_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name="Existencia mínima",
    )
    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["internal_code"]
        verbose_name = "Material controlado por cantidad"
        verbose_name_plural = "Materiales controlados por cantidad"
        constraints = [
            models.UniqueConstraint(
                fields=["specification", "unit_of_measure"],
                name="unique_stock_spec_unit",
            ),
            models.CheckConstraint(
                condition=models.Q(minimum_stock__gte=0),
                name="stock_minimum_nonnegative",
            ),
        ]

    def clean(self):
        if (
            self.specification_id
            and self.specification.material_type.control_method
            != ControlMethod.QUANTITY
        ):
            raise ValidationError(
                {
                    "specification": (
                        "El tipo seleccionado no está configurado "
                        "para control por cantidad."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.internal_code = self.internal_code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.internal_code} - {self.specification}"


class StockBatchStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Disponible"
    OBSERVED = "OBSERVED", "Observado"
    EXPIRED = "EXPIRED", "Vencido"
    DEPLETED = "DEPLETED", "Agotado"
    DISCHARGED = "DISCHARGED", "Dado de baja"


class StockBatch(TimeStampedModel):
    """
    Existencia concreta por unidad, depósito y lote.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    stock_material = models.ForeignKey(
        StockMaterial,
        on_delete=models.PROTECT,
        related_name="batches",
        verbose_name="Material",
    )
    lot_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de lote",
    )
    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.PROTECT,
        related_name="stock_batches",
        verbose_name="Unidad responsable",
    )
    armory = models.ForeignKey(
        Armory,
        on_delete=models.PROTECT,
        related_name="stock_batches",
        verbose_name="Armería o depósito actual",
    )
    initial_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name="Cantidad inicial",
    )
    current_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name="Cantidad actual",
    )
    manufacture_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de fabricación",
    )
    expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento",
    )
    status = models.CharField(
        max_length=20,
        choices=StockBatchStatus.choices,
        default=StockBatchStatus.AVAILABLE,
        db_index=True,
        verbose_name="Estado",
    )
    physical_condition = models.CharField(
        max_length=30,
        choices=PhysicalCondition.choices,
        default=PhysicalCondition.UNVERIFIED,
        verbose_name="Estado físico",
    )
    acquisition_source = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Procedencia o forma de adquisición",
    )
    registration_document = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Documento de alta o registro",
    )
    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Registro activo",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stock_batches",
        null=True,
        blank=True,
        verbose_name="Registrado por",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_stock_batches",
        null=True,
        blank=True,
        verbose_name="Última modificación por",
    )

    class Meta:
        ordering = [
            "stock_material__internal_code",
            "lot_number",
        ]
        verbose_name = "Lote o existencia"
        verbose_name_plural = "Lotes o existencias"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(initial_quantity__gt=0),
                name="batch_initial_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(current_quantity__gte=0),
                name="batch_current_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    current_quantity__lte=models.F(
                        "initial_quantity"
                    )
                ),
                name="batch_current_not_above_initial",
            ),
        ]
        indexes = [
            models.Index(
                fields=["unit", "status"],
                name="stockbatch_unit_status_idx",
            ),
            models.Index(
                fields=["armory", "status"],
                name="stock_armory_status_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.armory_id
            and self.unit_id
            and self.armory.unit_id != self.unit_id
        ):
            errors["armory"] = (
                "La armería o depósito no pertenece "
                "a la unidad responsable."
            )

        if (
            self.manufacture_date
            and self.expiration_date
            and self.expiration_date < self.manufacture_date
        ):
            errors["expiration_date"] = (
                "La fecha de vencimiento no puede ser anterior "
                "a la fecha de fabricación."
            )

        if (
            self.current_quantity is not None
            and self.initial_quantity is not None
            and self.current_quantity > self.initial_quantity
        ):
            errors["current_quantity"] = (
                "La cantidad actual no puede superar "
                "la cantidad inicial."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.lot_number = self.lot_number.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        lot = self.lot_number or "SIN LOTE"
        return f"{self.stock_material} - {lot}"


class ComponentType(TimeStampedModel):
    """
    Componentes del material principal.
    Ejemplos: CARGADOR, CORREA, ESTUCHE.
    El CUCHILLO BAYONETA no se registra aquí.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Tipo de componente",
    )
    is_serialized = models.BooleanField(
        default=False,
        verbose_name="Tiene identificación individual",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Tipo de componente"
        verbose_name_plural = "Tipos de componentes"

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SerializedMaterialComponent(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    material = models.ForeignKey(
        SerializedMaterial,
        on_delete=models.CASCADE,
        related_name="components",
        verbose_name="Material principal",
    )
    component_type = models.ForeignKey(
        ComponentType,
        on_delete=models.PROTECT,
        related_name="material_components",
        verbose_name="Tipo de componente",
    )
    identification_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Número de identificación",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Cantidad",
    )
    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = [
            "material__institutional_code",
            "component_type__name",
        ]
        verbose_name = "Componente de material"
        verbose_name_plural = "Componentes de material"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="component_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=[
                    "component_type",
                    "identification_number",
                ],
                name="unique_component_ident",
            ),
        ]

    def clean(self):
        errors = {}

        if self.component_type_id:
            if (
                self.component_type.is_serialized
                and not self.identification_number
            ):
                errors["identification_number"] = (
                    "Este componente requiere un número "
                    "de identificación."
                )

            if (
                self.component_type.is_serialized
                and self.quantity != 1
            ):
                errors["quantity"] = (
                    "Un componente individual debe registrarse "
                    "con cantidad igual a 1."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.identification_number:
            self.identification_number = (
                self.identification_number.strip().upper()
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.component_type.name} - "
            f"{self.material.institutional_code}"
        )