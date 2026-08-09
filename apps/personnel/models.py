import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Personnel(models.Model):
    """
    Representa al personal militar registrado en el sistema.

    Una persona puede existir aquí aunque no tenga
    una cuenta de acceso al sistema.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # -----------------------------
    # Identificación institucional
    # -----------------------------

    tin = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name="TIN",
    )

    # -----------------------------
    # Carnet de identidad
    # -----------------------------

    identity_card_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Número de carnet de identidad",
    )

    identity_card_complement = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Complemento del CI",
    )

    identity_card_issued_in = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Lugar de expedición del CI",
    )

    # -----------------------------
    # Nombres
    # -----------------------------

    first_name = models.CharField(
        max_length=100,
        verbose_name="Nombres",
    )

    paternal_last_name = models.CharField(
        max_length=100,
        verbose_name="Apellido paterno",
    )

    maternal_last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Apellido materno",
    )

    # -----------------------------
    # Datos militares
    # -----------------------------

    rank = models.ForeignKey(
        "organization.Rank",
        on_delete=models.PROTECT,
        related_name="personnel",
        null=True,
        blank=True,
        verbose_name="Grado",
    )

    position = models.ForeignKey(
        "organization.Position",
        on_delete=models.PROTECT,
        related_name="personnel",
        null=True,
        blank=True,
        verbose_name="Cargo",
    )

    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.PROTECT,
        related_name="personnel",
        null=True,
        blank=True,
        verbose_name="Unidad",
    )

    section = models.ForeignKey(
        "organization.Section",
        on_delete=models.PROTECT,
        related_name="personnel",
        null=True,
        blank=True,
        verbose_name="Sección",
    )

    graduation_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Año de egreso",
    )

    # -----------------------------
    # COSSMIL
    # -----------------------------

    cossmil_card_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Número de carnet COSSMIL",
    )

    cossmil_expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento COSSMIL",
    )

    # -----------------------------
    # Licencia de conducir
    # -----------------------------

    has_driver_license = models.BooleanField(
        default=False,
        verbose_name="Tiene licencia de conducir",
    )

    driver_license_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Número de licencia de conducir",
    )

    driver_license_category = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Categoría de licencia",
    )

    driver_license_expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento de licencia",
    )

    # -----------------------------
    # Estado y observaciones
    # -----------------------------

    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Personal activo",
    )

    # -----------------------------
    # Auditoría temporal
    # -----------------------------

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
            "paternal_last_name",
            "maternal_last_name",
            "first_name",
        ]

        verbose_name = "Personal militar"
        verbose_name_plural = "Personal militar"

        indexes = [
            models.Index(
                fields=["unit", "is_active"],
                name="personnel_unit_active_idx",
            ),
            models.Index(
                fields=["rank", "is_active"],
                name="personnel_rank_active_idx",
            ),
        ]

    @property
    def full_name(self):
        parts = [
            self.first_name,
            self.paternal_last_name,
            self.maternal_last_name,
        ]

        return " ".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    def clean(self):
        errors = {}

        # Normalización del CI
        self.identity_card_number = (
            self.identity_card_number.strip().upper()
            if self.identity_card_number
            else None
        )

        self.identity_card_complement = (
            self.identity_card_complement.strip().upper()
            if self.identity_card_complement
            else ""
        )

        self.identity_card_issued_in = (
            self.identity_card_issued_in.strip().upper()
            if self.identity_card_issued_in
            else ""
        )

        # Normalización COSSMIL
        self.cossmil_card_number = (
            self.cossmil_card_number.strip().upper()
            if self.cossmil_card_number
            else None
        )

        # Normalización licencia
        self.driver_license_number = (
            self.driver_license_number.strip().upper()
            if self.driver_license_number
            else None
        )

        self.driver_license_category = (
            self.driver_license_category.strip().upper()
            if self.driver_license_category
            else ""
        )

        # La sección debe pertenecer a la unidad.
        if (
            self.section_id
            and self.unit_id
            and self.section.unit_id != self.unit_id
        ):
            errors["section"] = (
                "La sección seleccionada no pertenece "
                "a la unidad indicada."
            )

        # Validación de licencia
        if self.has_driver_license:
            if not self.driver_license_number:
                errors["driver_license_number"] = (
                    "Debe registrar el número de licencia."
                )

            if not self.driver_license_category:
                errors["driver_license_category"] = (
                    "Debe registrar la categoría de la licencia."
                )

        else:
            self.driver_license_number = None
            self.driver_license_category = ""
            self.driver_license_expiration_date = None

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.tin = self.tin.strip().upper()

        self.first_name = self.first_name.strip().upper()

        self.paternal_last_name = (
            self.paternal_last_name.strip().upper()
        )

        self.maternal_last_name = (
            self.maternal_last_name.strip().upper()
            if self.maternal_last_name
            else ""
        )

        super().save(*args, **kwargs)

    def __str__(self):
        if self.rank:
            return (
                f"{self.rank.abbreviation} "
                f"{self.full_name} - TIN {self.tin}"
            )

        return f"{self.full_name} - TIN {self.tin}"