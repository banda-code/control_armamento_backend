from django.contrib.auth import password_validation
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from rest_framework import serializers

from apps.audit.utils import log_event
from apps.personnel.models import Personnel

from .models import User
from .scopes import get_user_unit
from .validators import (
    normalize_institutional_email,
    validate_institutional_email,
)

def raise_drf_validation_error(exc):
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


# ============================================================
# SERIALIZER DE CONSULTA DE USUARIO
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    """
    Representa una cuenta de usuario.

    Los datos personales y militares se obtienen
    desde Personnel.

    Los datos de autenticación y autorización
    continúan perteneciendo a User.
    """

    # --------------------------------------------------------
    # Relación Personnel -> datos personales
    # --------------------------------------------------------

    tin = serializers.CharField(
        source="personnel.tin",
        read_only=True,
        default=None,
    )

    identity_card_number = serializers.CharField(
        source="personnel.identity_card_number",
        read_only=True,
        default=None,
    )

    identity_card_complement = serializers.CharField(
        source="personnel.identity_card_complement",
        read_only=True,
        default="",
    )

    identity_card_issued_in = serializers.CharField(
        source="personnel.identity_card_issued_in",
        read_only=True,
        default="",
    )

    cossmil_card_number = serializers.CharField(
        source="personnel.cossmil_card_number",
        read_only=True,
        default=None,
    )

    cossmil_expiration_date = serializers.DateField(
        source="personnel.cossmil_expiration_date",
        read_only=True,
        default=None,
    )

    has_driver_license = serializers.BooleanField(
        source="personnel.has_driver_license",
        read_only=True,
        default=False,
    )

    driver_license_number = serializers.CharField(
        source="personnel.driver_license_number",
        read_only=True,
        default=None,
    )

    driver_license_category = serializers.CharField(
        source="personnel.driver_license_category",
        read_only=True,
        default="",
    )

    driver_license_expiration_date = serializers.DateField(
        source="personnel.driver_license_expiration_date",
        read_only=True,
        default=None,
    )

    first_name = serializers.CharField(
        source="personnel.first_name",
        read_only=True,
        default=None,
    )

    paternal_last_name = serializers.CharField(
        source="personnel.paternal_last_name",
        read_only=True,
        default=None,
    )

    maternal_last_name = serializers.CharField(
        source="personnel.maternal_last_name",
        read_only=True,
        default="",
    )

    full_name = serializers.CharField(
        source="personnel.full_name",
        read_only=True,
        default=None,
    )

    # --------------------------------------------------------
    # Grado
    # --------------------------------------------------------

    rank = serializers.UUIDField(
        source="personnel.rank_id",
        read_only=True,
        allow_null=True,
        default=None,
    )

    rank_name = serializers.CharField(
        source="personnel.rank.name",
        read_only=True,
        default=None,
    )

    rank_abbreviation = serializers.CharField(
        source="personnel.rank.abbreviation",
        read_only=True,
        default=None,
    )

    # --------------------------------------------------------
    # Cargo
    # --------------------------------------------------------

    position = serializers.UUIDField(
        source="personnel.position_id",
        read_only=True,
        allow_null=True,
        default=None,
    )

    position_name = serializers.CharField(
        source="personnel.position.name",
        read_only=True,
        default=None,
    )

    # --------------------------------------------------------
    # Unidad
    # --------------------------------------------------------

    unit = serializers.UUIDField(
        source="personnel.unit_id",
        read_only=True,
        allow_null=True,
        default=None,
    )

    unit_name = serializers.CharField(
        source="personnel.unit.name",
        read_only=True,
        default=None,
    )

    # --------------------------------------------------------
    # Sección
    # --------------------------------------------------------

    section = serializers.UUIDField(
        source="personnel.section_id",
        read_only=True,
        allow_null=True,
        default=None,
    )

    section_name = serializers.CharField(
        source="personnel.section.name",
        read_only=True,
        default=None,
    )

    # --------------------------------------------------------
    # Datos que siguen perteneciendo a User
    # --------------------------------------------------------

    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    has_global_scope = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = User

        fields = [
            "id",

            # Personnel
            "tin",
            "identity_card_number",
            "identity_card_complement",
            "identity_card_issued_in",
            "cossmil_card_number",
            "cossmil_expiration_date",
            "has_driver_license",
            "driver_license_number",
            "driver_license_category",
            "driver_license_expiration_date",
            "first_name",
            "paternal_last_name",
            "maternal_last_name",
            "full_name",
            "rank",
            "rank_name",
            "rank_abbreviation",
            "position",
            "position_name",
            "unit",
            "unit_name",
            "section",
            "section_name",

            # User
            "email",
            "role",
            "role_display",
            "has_global_scope",
            "must_change_password",
            "is_active",
            "last_login",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


# ============================================================
# CREACIÓN DE USUARIO
# ============================================================

class UserCreateSerializer(serializers.ModelSerializer):
    personnel = serializers.PrimaryKeyRelatedField(
        queryset=Personnel.objects.filter(
            is_active=True
        ),
    )

    temporary_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={
            "input_type": "password"
        },
    )

    class Meta:
        model = User

        fields = [
            "id",
            "personnel",
            "email",
            "role",
            "temporary_password",
        ]

        read_only_fields = [
            "id",
        ]

    def validate_email(self, value):
        value = normalize_institutional_email(
            value
        )

        validate_institutional_email(
            value
        )

        return value

    def validate_personnel(self, value):
        """
        Una persona solamente puede tener
        una cuenta de usuario asociada.
        """

        if User.objects.filter(
            personnel=value
        ).exists():
            raise serializers.ValidationError(
                "Este personal militar ya tiene "
                "una cuenta de usuario asociada."
            )

        return value

    def validate_temporary_password(
        self,
        value,
    ):
        password_validation.validate_password(
            value
        )

        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Crea solamente la cuenta de acceso.

        Los datos personales y militares
        ya existen previamente en Personnel.
        """

        temporary_password = (
            validated_data.pop(
                "temporary_password"
            )
        )

        personnel = validated_data.pop(
            "personnel"
        )

        request = self.context["request"]

        try:
            user = User.objects.create_user(
                personnel=personnel,
                email=validated_data["email"],
                password=temporary_password,
                role=validated_data["role"],
                created_by=request.user,
                must_change_password=True,
            )
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        log_event(
            request=request,
            action="USER_CREATED",
            actor=request.user,
            target=user,
            unit=get_user_unit(user),
            metadata={
                "role": user.role,
                "email": user.email,
                "tin": personnel.tin,
                "personnel_id": str(
                    personnel.id
                ),
            },
        )

        return user


# ============================================================
# ACTUALIZACIÓN DE USUARIO
# ============================================================

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        fields = [
            "email",
            "role",
        ]

    def validate_email(self, value):
        value = normalize_institutional_email(
            value
        )

        validate_institutional_email(
            value
        )

        return value

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        personnel = instance.personnel

        if not personnel:
            raise serializers.ValidationError(
                {
                    "personnel": [
                        (
                            "La cuenta no tiene un registro "
                            "de personal militar asociado."
                        )
                    ]
                }
            )

        previous_data = {
            "email": instance.email,
            "role": instance.role,
            "tin": personnel.tin,
            "unit_id": (
                str(personnel.unit_id)
                if personnel.unit_id
                else None
            ),
        }

        if "email" in validated_data:
            instance.email = (
                validated_data["email"]
            )

        if "role" in validated_data:
            instance.role = (
                validated_data["role"]
            )

        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        instance.save()

        request = self.context["request"]

        log_event(
            request=request,
            action="USER_UPDATED",
            actor=request.user,
            target=instance,
            unit=get_user_unit(instance),
            metadata={
                "before": previous_data,
                "after": {
                    "email": instance.email,
                    "role": instance.role,
                    "tin": personnel.tin,
                    "unit_id": (
                        str(personnel.unit_id)
                        if personnel.unit_id
                        else None
                    ),
                },
            },
        )

        return instance


# ============================================================
# LOGIN
# ============================================================

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={
            "input_type": "password"
        },
    )

    def validate_email(self, value):
        return normalize_institutional_email(
            value
        )


# ============================================================
# CAMBIO DE CONTRASEÑA
# ============================================================

class PasswordChangeSerializer(
    serializers.Serializer
):
    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_new_password(
        self,
        value,
    ):
        user = self.context[
            "request"
        ].user

        password_validation.validate_password(
            value,
            user=user,
        )

        return value


# ============================================================
# SOLICITUD DE RECUPERACIÓN
# ============================================================

class PasswordResetRequestSerializer(
    serializers.Serializer
):
    email = serializers.EmailField()

    def validate_email(self, value):
        return normalize_institutional_email(
            value
        )


# ============================================================
# CONFIRMACIÓN DE RECUPERACIÓN
# ============================================================

class PasswordResetConfirmSerializer(
    serializers.Serializer
):
    uid = serializers.CharField()

    token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_new_password(
        self,
        value,
    ):
        password_validation.validate_password(
            value
        )

        return value


# ============================================================
# CONTRASEÑA TEMPORAL
# ============================================================

class TemporaryPasswordSerializer(
    serializers.Serializer
):
    temporary_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_temporary_password(
        self,
        value,
    ):
        password_validation.validate_password(
            value
        )

        return value


# ============================================================
# RESPUESTAS SWAGGER
# ============================================================

class DetailResponseSerializer(
    serializers.Serializer
):
    """
    Respuesta sencilla utilizada por endpoints
    que devuelven un mensaje informativo.
    """

    detail = serializers.CharField()


class JwtRefreshResponseSerializer(
    serializers.Serializer
):
    """
    Respuesta generada al renovar el access token.
    """

    access = serializers.CharField()

    token_type = serializers.CharField()

    expires_in = serializers.IntegerField()


class JwtLoginResponseSerializer(
    serializers.Serializer
):
    """
    Respuesta devuelta después de iniciar sesión.
    """

    detail = serializers.CharField()

    access = serializers.CharField()

    token_type = serializers.CharField()

    expires_in = serializers.IntegerField()

    must_change_password = (
        serializers.BooleanField()
    )

    user = UserSerializer()