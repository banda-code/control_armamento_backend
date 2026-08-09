import uuid

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


class Institution(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="Institución",
    )
    acronym = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Sigla",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Institución"
        verbose_name_plural = "Instituciones"

    def __str__(self):
        return self.name


class Unit(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="units",
        verbose_name="Institución",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Unidad",
    )
    acronym = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Sigla",
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name="Código",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subunits",
        null=True,
        blank=True,
        verbose_name="Unidad superior",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_unit_name_per_institution",
            )
        ]

    def __str__(self):
        if self.acronym:
            return f"{self.name} ({self.acronym})"
        return self.name


class Rank(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Grado",
    )
    abbreviation = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Abreviatura",
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Orden",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Grado"
        verbose_name_plural = "Grados"

    def __str__(self):
        return self.abbreviation


class Position(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Cargo",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"

    def __str__(self):
        return self.name


class Section(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="sections",
        verbose_name="Unidad",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Sección",
    )
    code = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Código",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = ["unit__name", "name"]
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "name"],
                name="unique_section_name_per_unit",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.unit.name}"
