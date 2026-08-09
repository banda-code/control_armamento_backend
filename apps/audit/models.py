import uuid

from django.conf import settings
from django.db import models


class AuditOutcome(models.TextChoices):
    SUCCESS = "SUCCESS", "Correcto"
    FAILED = "FAILED", "Fallido"


class AuditLog(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
        verbose_name="Usuario",
    )
    unit = models.ForeignKey(
        "organization.Unit",
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
        verbose_name="Unidad",
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Acción",
    )
    outcome = models.CharField(
        max_length=20,
        choices=AuditOutcome.choices,
        default=AuditOutcome.SUCCESS,
        verbose_name="Resultado",
    )
    target_model = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Modelo afectado",
    )
    target_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID afectado",
    )
    target_repr = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Registro afectado",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP",
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="Navegador o dispositivo",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos adicionales",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Fecha y hora",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Evento de auditoría"
        verbose_name_plural = "Eventos de auditoría"
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["unit", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self):
        actor = self.actor.email if self.actor else "Anónimo"
        return f"{self.action} - {actor} - {self.created_at}"
