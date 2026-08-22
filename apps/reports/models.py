import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.organization.models import Unit
from apps.personnel.models import Personnel


class IndividualFiliationConfig(models.Model):
    """
    Configuración de responsables que firman el
    Registro de Armamento de Dotación Individual.

    Existe una configuración por cada unidad.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    unit = models.OneToOneField(
        Unit,
        on_delete=models.PROTECT,
        related_name="individual_filiation_config",
        verbose_name="Unidad",
    )

    verification_responsible = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filiation_configs_as_verifier",
        verbose_name="Responsable de la verificación",
    )

    logistics_chief = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filiation_configs_as_logistics_chief",
        verbose_name="Jefe de la Sección IV Logística",
    )

    unit_commander = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filiation_configs_as_unit_commander",
        verbose_name="Comandante de la unidad",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualización",
    )

    class Meta:
        verbose_name = "Configuración de filiación individual"
        verbose_name_plural = "Configuraciones de filiación individual"
        ordering = ["unit__name"]

    def __str__(self):
        return f"Filiación individual - {self.unit.name}"

    def clean(self):
        errors = {}

        responsables = {
            "verification_responsible": self.verification_responsible,
            "logistics_chief": self.logistics_chief,
            "unit_commander": self.unit_commander,
        }

        for field_name, person in responsables.items():
            if person and person.unit_id != self.unit_id:
                errors[field_name] = (
                    "El personal seleccionado debe pertenecer "
                    "a la misma unidad de la configuración."
                )

        if errors:
            raise ValidationError(errors)