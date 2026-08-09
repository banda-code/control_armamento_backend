from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(
        source="actor.email",
        read_only=True,
        default=None,
    )
    actor_name = serializers.CharField(
        source="actor.full_name",
        read_only=True,
        default=None,
    )
    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
        default=None,
    )
    outcome_display = serializers.CharField(
        source="get_outcome_display",
        read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "actor_name",
            "unit",
            "unit_name",
            "action",
            "outcome",
            "outcome_display",
            "target_model",
            "target_id",
            "target_repr",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
