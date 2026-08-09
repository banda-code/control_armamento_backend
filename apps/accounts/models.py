import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models

from .managers import UserManager
from .validators import (
    normalize_institutional_email,
    validate_institutional_email,
)


class UserRole(models.TextChoices):
    ADMINISTRATOR = (
        "ADMINISTRATOR",
        "Administrador",
    )

    NAVY_COMMAND = (
        "NAVY_COMMAND",
        "Comando de la Armada",
    )

    UNIT_COMMANDER = (
        "UNIT_COMMANDER",
        "Comandante de Unidad",
    )

    LOGISTICS_CHIEF = (
        "LOGISTICS_CHIEF",
        "Jefe de Cuarta Sección - Logística",
    )

    ARMAMENT_OFFICER = (
        "ARMAMENT_OFFICER",
        "Encargado de Armamento",
    )


class User(
    AbstractBaseUser,
    PermissionsMixin,
):
    """
    Cuenta de acceso al sistema.

    Los datos personales y militares
    pertenecen exclusivamente a Personnel.

    Un superusuario técnico puede existir
    sin Personnel asociado.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    personnel = models.OneToOneField(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="user_account",
        null=True,
        blank=True,
        verbose_name="Personal militar asociado",
    )

    email = models.EmailField(
        unique=True,
        db_index=True,
        validators=[
            validate_institutional_email
        ],
        verbose_name="Correo institucional",
    )

    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        verbose_name="Rol",
    )

    must_change_password = models.BooleanField(
        default=True,
        verbose_name="Debe cambiar contraseña",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Cuenta activa",
    )

    is_staff = models.BooleanField(
        default=False,
        verbose_name=(
            "Acceso a administración Django"
        ),
    )

    created_by = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="created_users",
        null=True,
        blank=True,
        verbose_name="Creado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualización",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    # Ya no solicitamos TIN ni nombres al
    # ejecutar createsuperuser.
    REQUIRED_FIELDS = []

    class Meta:
        ordering = [
            "email",
        ]

        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def clean(self):
        super().clean()

        self.email = normalize_institutional_email(
            self.email
        )

        errors = {}

        # -----------------------------------------------------
        # Relación con Personnel
        # -----------------------------------------------------

        # El superusuario técnico puede existir
        # sin un Personnel asociado.
        #
        # Toda cuenta institucional normal
        # necesita corresponder a una persona.
        if (
            not self.is_superuser
            and not self.personnel_id
        ):
            errors["personnel"] = (
                "La cuenta debe estar asociada "
                "a un registro de personal militar."
            )

        personnel = None

        if self.personnel_id:
            personnel = self.personnel

        # -----------------------------------------------------
        # Reglas de acuerdo con el rol
        # -----------------------------------------------------

        if personnel:
            unit_roles = {
                UserRole.UNIT_COMMANDER,
                UserRole.LOGISTICS_CHIEF,
                UserRole.ARMAMENT_OFFICER,
            }

            if (
                self.role in unit_roles
                and not personnel.unit_id
            ):
                errors["personnel"] = (
                    "El personal asociado a este rol "
                    "debe pertenecer a una unidad."
                )

            if (
                self.role
                != UserRole.ADMINISTRATOR
                and not personnel.rank_id
            ):
                errors["personnel"] = (
                    "El personal asociado debe tener "
                    "un grado registrado."
                )

            if (
                self.role
                != UserRole.ADMINISTRATOR
                and not personnel.position_id
            ):
                errors["personnel"] = (
                    "El personal asociado debe tener "
                    "un cargo registrado."
                )

        if errors:
            raise ValidationError(
                errors
            )

    def save(
        self,
        *args,
        **kwargs,
    ):
        self.email = normalize_institutional_email(
            self.email
        )

        # Solamente Administrador y superusuario
        # tienen acceso al Django Admin.
        self.is_staff = bool(
            self.is_superuser
            or self.role
            == UserRole.ADMINISTRATOR
        )

        super().save(
            *args,
            **kwargs,
        )

    @property
    def full_name(self):
        """
        Nombre del usuario obtenido desde Personnel.

        Para un superusuario técnico sin Personnel,
        se utiliza el correo.
        """

        if self.personnel_id:
            return self.personnel.full_name

        return self.email

    @property
    def has_global_scope(self):
        """
        Indica si el usuario puede consultar
        información de todas las unidades.
        """

        return bool(
            self.is_superuser
            or self.role
            in {
                UserRole.ADMINISTRATOR,
                UserRole.NAVY_COMMAND,
            }
        )

    def __str__(self):
        if self.personnel_id:
            return (
                f"{self.full_name} - "
                f"TIN {self.personnel.tin}"
            )

        return self.email