from rest_framework import (
    filters,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.scopes import get_user_unit_id
from apps.audit.utils import log_event

from .models import IndividualAssignment
from .permissions import IndividualAssignmentPermission
from .serializers import (
    IndividualAssignmentCreateSerializer,
    IndividualAssignmentReturnSerializer,
    IndividualAssignmentSerializer,
)


class IndividualAssignmentViewSet(
    viewsets.ModelViewSet
):
    """
    Gestión de dotaciones individuales.

    Permite:
    - listar dotaciones,
    - consultar detalle,
    - registrar una nueva dotación,
    - registrar la devolución.

    No permite:
    - DELETE,
    - PUT,
    - PATCH general.
    """

    queryset = (
        IndividualAssignment.objects
        .select_related(
            "personnel",
            "personnel__rank",
            "personnel__unit",
            "material",
            "material__specification",
            "material__unit",
            "material__armory",
            "assigned_by",
            "returned_by",
        )
        .prefetch_related(
            "assigned_components__component__component_type"
        )
        .all()
    )

    permission_classes = [
        IndividualAssignmentPermission,
    ]

    http_method_names = [
        "get",
        "post",
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
        "personnel__tin",
        "personnel__first_name",
        "personnel__paternal_last_name",
        "personnel__maternal_last_name",
        "material__institutional_code",
        "material__identification_number",
        "material__specification__name",
        "material__unit__name",
        "assignment_document",
        "return_document",
    ]

    # ---------------------------------------------------------
    # Ordenamiento
    # ---------------------------------------------------------

    ordering_fields = [
        "assigned_at",
        "returned_at",
        "created_at",
        "updated_at",
        "status",
    ]

    ordering = [
        "-assigned_at",
    ]

    # ---------------------------------------------------------
    # Serializer según operación
    # ---------------------------------------------------------

    def get_serializer_class(self):
        if self.action == "create":
            return IndividualAssignmentCreateSerializer

        if self.action == "return_assignment":
            return IndividualAssignmentReturnSerializer

        return IndividualAssignmentSerializer

    # ---------------------------------------------------------
    # Alcance por unidad
    # ---------------------------------------------------------

    def get_queryset(self):
        queryset = self.queryset

        # Swagger necesita conocer el modelo
        # sin aplicar el alcance del usuario.
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
            user_unit_id = get_user_unit_id(
                user
            )

            if not user_unit_id:
                return queryset.none()

            scoped_queryset = queryset.filter(
                material__unit_id=user_unit_id
            )

        # -----------------------------------------------------
        # Filtros opcionales
        # -----------------------------------------------------

        assignment_status = (
            self.request.query_params.get(
                "status"
            )
        )

        personnel_id = (
            self.request.query_params.get(
                "personnel"
            )
        )

        material_id = (
            self.request.query_params.get(
                "material"
            )
        )

        unit_id = (
            self.request.query_params.get(
                "unit"
            )
        )

        if assignment_status:
            scoped_queryset = (
                scoped_queryset.filter(
                    status=assignment_status
                )
            )

        if personnel_id:
            scoped_queryset = (
                scoped_queryset.filter(
                    personnel_id=personnel_id
                )
            )

        if material_id:
            scoped_queryset = (
                scoped_queryset.filter(
                    material_id=material_id
                )
            )

        # Solo usuarios de alcance global
        # pueden solicitar expresamente
        # cualquier unidad.
        if (
            unit_id
            and user.has_global_scope
        ):
            scoped_queryset = (
                scoped_queryset.filter(
                    material__unit_id=unit_id
                )
            )

        return scoped_queryset

    # ---------------------------------------------------------
    # Registrar entrega
    # ---------------------------------------------------------

    def perform_create(
        self,
        serializer,
    ):
        assignment = serializer.save()

        log_event(
            request=self.request,
            action="INDIVIDUAL_ASSIGNMENT_CREATED",
            actor=self.request.user,
            target=assignment,
            unit=assignment.material.unit,
            metadata={
                "personnel_tin": (
                    assignment.personnel.tin
                ),
                "material_code": (
                    assignment
                    .material
                    .institutional_code
                ),
                "material_identification_number": (
                    assignment
                    .material
                    .identification_number
                ),
                "status": assignment.status,
            },
        )

    # ---------------------------------------------------------
    # Registrar devolución
    # ---------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="return",
        url_name="return",
    )
    def return_assignment(
        self,
        request,
        pk=None,
    ):
        # get_object() también ejecuta
        # has_object_permission().
        assignment = self.get_object()

        serializer = self.get_serializer(
            assignment,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True
        )

        assignment = serializer.save()

        log_event(
            request=request,
            action="INDIVIDUAL_ASSIGNMENT_RETURNED",
            actor=request.user,
            target=assignment,
            unit=assignment.material.unit,
            metadata={
                "personnel_tin": (
                    assignment.personnel.tin
                ),
                "material_code": (
                    assignment
                    .material
                    .institutional_code
                ),
                "status": assignment.status,
                "returned_at": (
                    assignment.returned_at.isoformat()
                    if assignment.returned_at
                    else None
                ),
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )