from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.accounts.models import (
    User,
    UserRole,
)
from apps.organization.models import (
    Institution,
    Position,
    Unit,
)


class Command(BaseCommand):
    help = (
        "Crea la institución, la unidad Comando General, "
        "los cargos iniciales y el Administrador técnico."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-email",
            required=True,
            help=(
                "Correo @armada.mil.bo "
                "del Administrador técnico."
            ),
        )

        parser.add_argument(
            "--admin-password",
            required=True,
            help=(
                "Contraseña inicial "
                "del Administrador técnico."
            ),
        )

    def handle(self, *args, **options):
        institution, _ = Institution.objects.get_or_create(
            name="Armada Boliviana",
            defaults={
                "acronym": "AB",
            },
        )

        command_unit, _ = Unit.objects.get_or_create(
            code="CGAB",
            defaults={
                "institution": institution,
                "name": (
                    "Comando General de la "
                    "Armada Boliviana"
                ),
                "acronym": "CGAB",
            },
        )

        initial_positions = [
            "Administrador del Sistema",
            "Comando de la Armada",
            "Comandante de Unidad",
            "Jefe de Cuarta Sección - Logística",
            "Encargado de Armamento",
        ]

        for name in initial_positions:
            Position.objects.get_or_create(
                name=name
            )

        email = (
            options["admin_email"]
            .strip()
            .lower()
        )

        if User.objects.filter(
            email=email
        ).exists():
            raise CommandError(
                (
                    "Ya existe un usuario con "
                    f"el correo {email}."
                )
            )

        admin = User.objects.create_superuser(
            email=email,
            password=options["admin_password"],
            role=UserRole.ADMINISTRATOR,
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Administrador técnico creado "
                    f"correctamente: {admin.email}"
                )
            )
        )