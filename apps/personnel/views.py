from rest_framework import (
    filters,
    viewsets,
)

from apps.accounts.scopes import (
    get_user_unit_id,
)
from apps.audit.utils import log_event

from .models import Personnel
from .permissions import PersonnelPermission
from .serializers import PersonnelSerializer


class PersonnelViewSet(viewsets.ModelViewSet):
    """
    Gestión del personal militar.

    Administrador:
        - consulta global
        - creación
        - actualización

    Comando de la Armada:
        - consulta global

    Roles de unidad:
        - consulta únicamente del personal
          perteneciente a su propia unidad

    No se permite eliminación física.
    """

    queryset = Personnel.objects.select_related(
        "rank",
        "position",
        "unit",
        "section",
        "user_account",
    ).all()

    serializer_class = PersonnelSerializer

    permission_classes = [
        PersonnelPermission,
    ]

    # No permitimos PUT ni DELETE.
    # Las modificaciones se realizan con PATCH.
    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    # ---------------------------------------------------------
    # Búsqueda
    # ---------------------------------------------------------

    search_fields = [
        "tin",
        "identity_card_number",
        "first_name",
        "paternal_last_name",
        "maternal_last_name",
        "cossmil_card_number",
        "driver_license_number",
        "rank__name",
        "rank__abbreviation",
        "position__name",
        "unit__name",
        "unit__acronym",
        "unit__code",
        "section__name",
        "section__code",
        "user_account__email",
    ]

    # ---------------------------------------------------------
    # Ordenamiento
    # ---------------------------------------------------------

    ordering_fields = [
        "tin",
        "first_name",
        "paternal_last_name",
        "maternal_last_name",
        "graduation_year",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "paternal_last_name",
        "maternal_last_name",
        "first_name",
    ]

    # ---------------------------------------------------------
    # Alcance por unidad
    # ---------------------------------------------------------

    def get_queryset(self):
        queryset = self.queryset

        # Durante la generación de Swagger
        # devolvemos el queryset base.
        if getattr(
            self,
            "swagger_fake_view",
            False,
        ):
            return queryset

        user = self.request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return queryset.none()

        # Administrador, superusuario y
        # Comando de la Armada tienen
        # alcance global.
        if user.has_global_scope:
            scoped_queryset = queryset

        else:
            # Los demás usuarios obtienen
            # la unidad desde:
            #
            # User -> Personnel -> Unit
            unit_id = get_user_unit_id(
                user
            )

            if not unit_id:
                return queryset.none()

            scoped_queryset = queryset.filter(
                unit_id=unit_id
            )

        # -----------------------------------------------------
        # Filtros opcionales
        # -----------------------------------------------------

        is_active = (
            self.request.query_params.get(
                "is_active"
            )
        )

        unit_id = (
            self.request.query_params.get(
                "unit"
            )
        )

        rank_id = (
            self.request.query_params.get(
                "rank"
            )
        )

        position_id = (
            self.request.query_params.get(
                "position"
            )
        )

        # Personal activo / inactivo
        if is_active is not None:
            normalized = (
                str(is_active)
                .strip()
                .lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
                "si",
                "sí",
            }:
                scoped_queryset = (
                    scoped_queryset.filter(
                        is_active=True
                    )
                )

            elif normalized in {
                "false",
                "0",
                "no",
            }:
                scoped_queryset = (
                    scoped_queryset.filter(
                        is_active=False
                    )
                )

        # Solo usuarios con alcance global
        # pueden solicitar expresamente
        # otra unidad.
        if (
            unit_id
            and user.has_global_scope
        ):
            scoped_queryset = (
                scoped_queryset.filter(
                    unit_id=unit_id
                )
            )

        if rank_id:
            scoped_queryset = (
                scoped_queryset.filter(
                    rank_id=rank_id
                )
            )

        if position_id:
            scoped_queryset = (
                scoped_queryset.filter(
                    position_id=position_id
                )
            )

        return scoped_queryset

    # ---------------------------------------------------------
    # Auditoría de creación
    # ---------------------------------------------------------

    def perform_create(
        self,
        serializer,
    ):
        personnel = serializer.save()

        log_event(
            request=self.request,
            action="PERSONNEL_CREATED",
            actor=self.request.user,
            target=personnel,
            unit=personnel.unit,
            metadata={
                "tin": personnel.tin,
                "full_name": (
                    personnel.full_name
                ),
            },
        )

    # ---------------------------------------------------------
    # Auditoría de actualización
    # ---------------------------------------------------------

    def perform_update(
        self,
        serializer,
    ):
        personnel = serializer.save()

        log_event(
            request=self.request,
            action="PERSONNEL_UPDATED",
            actor=self.request.user,
            target=personnel,
            unit=personnel.unit,
            metadata={
                "tin": personnel.tin,
                "full_name": (
                    personnel.full_name
                ),
                "is_active": (
                    personnel.is_active
                ),
            },
        )