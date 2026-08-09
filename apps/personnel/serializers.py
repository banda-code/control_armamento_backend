from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError as DjangoValidationError,
)
from django.db import transaction

from rest_framework import serializers

from .models import Personnel


def raise_drf_validation_error(exc):
    """
    Convierte los errores de validación de Django
    en errores entendibles por Django REST Framework.
    """

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(
            exc.message_dict
        )

    raise serializers.ValidationError(
        {
            "non_field_errors": list(
                exc.messages
            )
        }
    )


class PersonnelSerializer(serializers.ModelSerializer):
    """
    Serializer principal del personal militar.

    Permite:
    - Registrar personal.
    - Consultar personal.
    - Actualizar datos personales y militares.

    También muestra información descriptiva
    de grado, cargo, unidad y sección.
    """

    # ---------------------------------------------------------
    # Datos descriptivos de organización
    # ---------------------------------------------------------

    rank_name = serializers.CharField(
        source="rank.name",
        read_only=True,
        default=None,
    )

    rank_abbreviation = serializers.CharField(
        source="rank.abbreviation",
        read_only=True,
        default=None,
    )

    position_name = serializers.CharField(
        source="position.name",
        read_only=True,
        default=None,
    )

    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
        default=None,
    )

    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
        default=None,
    )

    full_name = serializers.CharField(
        read_only=True,
    )

    # ---------------------------------------------------------
    # Información sobre cuenta de acceso
    # ---------------------------------------------------------

    has_user_account = serializers.SerializerMethodField()

    user_account_id = serializers.SerializerMethodField()

    user_account_email = serializers.SerializerMethodField()

    class Meta:
        model = Personnel

        fields = [
            "id",

            # Identificación institucional
            "tin",

            # Carnet de identidad
            "identity_card_number",
            "identity_card_complement",
            "identity_card_issued_in",

            # Nombres
            "first_name",
            "paternal_last_name",
            "maternal_last_name",
            "full_name",

            # Datos militares
            "rank",
            "rank_name",
            "rank_abbreviation",
            "position",
            "position_name",
            "unit",
            "unit_name",
            "section",
            "section_name",
            "graduation_year",

            # COSSMIL
            "cossmil_card_number",
            "cossmil_expiration_date",

            # Licencia
            "has_driver_license",
            "driver_license_number",
            "driver_license_category",
            "driver_license_expiration_date",

            # Estado
            "observations",
            "is_active",

            # Cuenta de acceso
            "has_user_account",
            "user_account_id",
            "user_account_email",

            # Auditoría temporal
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "full_name",
            "rank_name",
            "rank_abbreviation",
            "position_name",
            "unit_name",
            "section_name",
            "has_user_account",
            "user_account_id",
            "user_account_email",
            "created_at",
            "updated_at",
        ]

    # ---------------------------------------------------------
    # Cuenta User asociada
    # ---------------------------------------------------------

    def get_has_user_account(self, obj):
        try:
            obj.user_account
            return True
        except ObjectDoesNotExist:
            return False

    def get_user_account_id(self, obj):
        try:
            return obj.user_account.id
        except ObjectDoesNotExist:
            return None

    def get_user_account_email(self, obj):
        try:
            return obj.user_account.email
        except ObjectDoesNotExist:
            return None

    # ---------------------------------------------------------
    # Creación
    # ---------------------------------------------------------

    @transaction.atomic
    def create(self, validated_data):
        personnel = Personnel(
            **validated_data
        )

        try:
            personnel.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        personnel.save()

        return personnel

    # ---------------------------------------------------------
    # Actualización
    # ---------------------------------------------------------

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        for field, value in validated_data.items():
            setattr(
                instance,
                field,
                value,
            )

        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        instance.save()

        return instance