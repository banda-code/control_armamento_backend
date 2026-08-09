from django.contrib.auth.base_user import BaseUserManager

from .validators import normalize_institutional_email


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(
        self,
        email,
        password=None,
        personnel=None,
        **extra_fields,
    ):
        """
        Crea una cuenta de usuario.

        Los datos personales y militares
        pertenecen exclusivamente a Personnel.
        """

        if not email:
            raise ValueError(
                "El correo institucional es obligatorio."
            )

        email = normalize_institutional_email(
            email
        )

        if personnel is not None:
            extra_fields["personnel"] = personnel

        user = self.model(
            email=email,
            **extra_fields,
        )

        user.set_password(
            password
        )

        user.full_clean()

        user.save(
            using=self._db
        )

        return user

    def create_superuser(
        self,
        email,
        password=None,
        personnel=None,
        **extra_fields,
    ):
        """
        Crea un superusuario técnico.

        Personnel es opcional para este tipo
        de cuenta.
        """

        from .models import UserRole

        extra_fields.setdefault(
            "role",
            UserRole.ADMINISTRATOR,
        )

        extra_fields.setdefault(
            "is_staff",
            True,
        )

        extra_fields.setdefault(
            "is_superuser",
            True,
        )

        extra_fields.setdefault(
            "is_active",
            True,
        )

        extra_fields.setdefault(
            "must_change_password",
            False,
        )

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "El superusuario debe tener "
                "is_staff=True."
            )

        if (
            extra_fields.get("is_superuser")
            is not True
        ):
            raise ValueError(
                "El superusuario debe tener "
                "is_superuser=True."
            )

        return self.create_user(
            email=email,
            password=password,
            personnel=personnel,
            **extra_fields,
        )