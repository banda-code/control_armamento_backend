from rest_framework import filters, viewsets

from apps.accounts.scopes import get_user_unit_id
from apps.audit.utils import log_event

from .models import (
    Institution,
    Position,
    Rank,
    Section,
    Unit,
)
from .permissions import OrganizationPermission
from .serializers import (
    InstitutionSerializer,
    PositionSerializer,
    RankSerializer,
    SectionSerializer,
    UnitSerializer,
)


class AuditedCatalogViewSet(viewsets.ModelViewSet):
    """
    Vista base para los catálogos de organización.

    Permite:
    - Consultar
    - Crear
    - Actualizar parcialmente

    No permite eliminar registros físicamente.
    """

    permission_classes = [
        OrganizationPermission,
    ]

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

    def perform_create(self, serializer):
        instance = serializer.save()

        unit = (
            instance
            if isinstance(instance, Unit)
            else getattr(instance, "unit", None)
        )

        log_event(
            request=self.request,
            action="CATALOG_CREATED",
            target=instance,
            unit=unit,
        )

    def perform_update(self, serializer):
        instance = serializer.save()

        unit = (
            instance
            if isinstance(instance, Unit)
            else getattr(instance, "unit", None)
        )

        log_event(
            request=self.request,
            action="CATALOG_UPDATED",
            target=instance,
            unit=unit,
        )


class InstitutionViewSet(AuditedCatalogViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer

    search_fields = [
        "name",
        "acronym",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]


class UnitViewSet(AuditedCatalogViewSet):
    """
    Administrador y Comando de la Armada:
    pueden consultar todas las unidades.

    Los demás usuarios:
    solamente pueden consultar su propia unidad.
    """

    queryset = Unit.objects.select_related(
        "institution",
        "parent",
    ).all()

    serializer_class = UnitSerializer

    search_fields = [
        "name",
        "acronym",
        "code",
    ]

    ordering_fields = [
        "name",
        "code",
        "created_at",
    ]

    def get_queryset(self):
        queryset = self.queryset

        # Durante la generación de Swagger
        # devolvemos el queryset base.
        if getattr(self, "swagger_fake_view", False):
            return queryset

        user = self.request.user

        if not getattr(user, "is_authenticated", False):
            return queryset.none()

        # Administrador y Comando de la Armada
        # tienen alcance global.
        if user.has_global_scope:
            return queryset

        # Ahora obtenemos la unidad desde:
        # User -> Personnel -> Unit
        unit_id = get_user_unit_id(user)

        if not unit_id:
            return queryset.none()

        return queryset.filter(
            id=unit_id,
        )


class RankViewSet(AuditedCatalogViewSet):
    queryset = Rank.objects.all()
    serializer_class = RankSerializer

    search_fields = [
        "name",
        "abbreviation",
    ]

    ordering_fields = [
        "order",
        "name",
    ]


class PositionViewSet(AuditedCatalogViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer

    search_fields = [
        "name",
    ]

    ordering_fields = [
        "name",
    ]


class SectionViewSet(AuditedCatalogViewSet):
    """
    Administrador y Comando de la Armada:
    pueden consultar todas las secciones.

    Los demás usuarios:
    solamente pueden consultar las secciones
    correspondientes a su unidad.
    """

    queryset = Section.objects.select_related(
        "unit",
    ).all()

    serializer_class = SectionSerializer

    search_fields = [
        "name",
        "code",
        "unit__name",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]

    def get_queryset(self):
        queryset = self.queryset

        # Permite que Swagger reconozca
        # correctamente el modelo.
        if getattr(self, "swagger_fake_view", False):
            return queryset

        user = self.request.user

        if not getattr(user, "is_authenticated", False):
            return queryset.none()

        # Administrador y Comando de la Armada
        # tienen alcance global.
        if user.has_global_scope:
            return queryset

        # Ahora obtenemos la unidad desde:
        # User -> Personnel -> Unit
        unit_id = get_user_unit_id(user)

        if not unit_id:
            return queryset.none()

        return queryset.filter(
            unit_id=unit_id,
        )