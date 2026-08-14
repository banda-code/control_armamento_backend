from rest_framework import (
    filters,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.parsers import (
    FormParser,
    MultiPartParser,
)
from rest_framework.response import Response

from apps.accounts.scopes import get_user_unit_id
from apps.audit.utils import log_event

from .models import (
    AssignmentCustodyMovementType,
    IndividualAssignment,
    IndividualAssignmentCustodyMovement,
)
from .permissions import IndividualAssignmentPermission
from .serializers import (
    IndividualAssignmentCreateSerializer,
    IndividualAssignmentCustodyActionSerializer,
    IndividualAssignmentCustodyMovementSerializer,
    IndividualAssignmentPhotoSerializer,
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
    - cerrar definitivamente una dotación,
    - registrar fotografías,
    - entregar material del pañol al personal,
    - recibir material del personal en el pañol,
    - consultar historial de custodia.

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

    # =========================================================
    # SERIALIZER SEGÚN OPERACIÓN
    # =========================================================

    def get_serializer_class(self):
        if self.action == "create":
            return IndividualAssignmentCreateSerializer

        if self.action == "return_assignment":
            return IndividualAssignmentReturnSerializer

        if self.action == "photos":
            return IndividualAssignmentPhotoSerializer

        if self.action in {
            "custody_deliver",
            "custody_receive",
        }:
            return IndividualAssignmentCustodyActionSerializer

        if self.action == "custody_history":
            return IndividualAssignmentCustodyMovementSerializer

        return IndividualAssignmentSerializer

    # =========================================================
    # ALCANCE POR UNIDAD
    # =========================================================

    def get_queryset(self):
        queryset = self.queryset

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

        # Administrador / Comando Armada:
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

    # =========================================================
    # CREAR DOTACIÓN INDIVIDUAL
    # =========================================================

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

    # =========================================================
    # DEVOLUCIÓN DEFINITIVA / CIERRE DE DOTACIÓN
    # =========================================================

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

    # =========================================================
    # FOTOGRAFÍAS
    # =========================================================

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="photos",
        url_name="photos",
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def photos(
        self,
        request,
        pk=None,
    ):
        """
        GET:
            Lista fotografías.

        POST:
            Registra fotografía mediante
            multipart/form-data.
        """

        assignment = self.get_object()

        # -----------------------------------------------------
        # CONSULTAR
        # -----------------------------------------------------

        if request.method == "GET":
            photos = (
                assignment.photos
                .select_related(
                    "uploaded_by",
                )
                .all()
            )

            serializer = self.get_serializer(
                photos,
                many=True,
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------------------
        # REGISTRAR
        # -----------------------------------------------------

        serializer_context = (
            self.get_serializer_context()
        )

        serializer_context[
            "assignment"
        ] = assignment

        serializer = self.get_serializer(
            data=request.data,
            context=serializer_context,
        )

        serializer.is_valid(
            raise_exception=True
        )

        photo = serializer.save()

        log_event(
            request=request,
            action=(
                "INDIVIDUAL_ASSIGNMENT_PHOTO_UPLOADED"
            ),
            actor=request.user,
            target=assignment,
            unit=assignment.material.unit,
            metadata={
                "photo_id": str(photo.id),
                "moment": photo.moment,
                "photo_type": photo.photo_type,
                "description": photo.description,
                "material_code": (
                    assignment
                    .material
                    .institutional_code
                ),
                "personnel_tin": (
                    assignment.personnel.tin
                ),
            },
        )

        response_serializer = (
            self.get_serializer(
                photo
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # =========================================================
    # HISTORIAL DE CUSTODIA
    # =========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="custody-history",
        url_name="custody-history",
    )
    def custody_history(
        self,
        request,
    ):
        queryset = (
            IndividualAssignmentCustodyMovement
            .objects
            .select_related(
                "personnel",
                "unit",
                "armory",
                "created_by",
            )
            .prefetch_related(
                (
                    "items__assignment__material"
                    "__specification"
                ),
            )
            .all()
        )

        user = request.user

        # -----------------------------------------------------
        # ALCANCE POR UNIDAD
        # -----------------------------------------------------

        if not user.has_global_scope:
            user_unit_id = get_user_unit_id(
                user
            )

            if not user_unit_id:
                queryset = queryset.none()

            else:
                queryset = queryset.filter(
                    unit_id=user_unit_id
                )

        # -----------------------------------------------------
        # FILTROS
        # -----------------------------------------------------

        personnel_id = (
            request.query_params.get(
                "personnel"
            )
        )

        assignment_id = (
            request.query_params.get(
                "assignment"
            )
        )

        movement_type = (
            request.query_params.get(
                "movement_type"
            )
        )

        if personnel_id:
            queryset = queryset.filter(
                personnel_id=personnel_id
            )

        if assignment_id:
            queryset = queryset.filter(
                items__assignment_id=assignment_id
            )

        if movement_type:
            queryset = queryset.filter(
                movement_type=movement_type
            )

        queryset = queryset.distinct()

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # FUNCIÓN COMÚN PARA ENTREGA / RECEPCIÓN
    # =========================================================

    def _create_custody_action(
        self,
        *,
        request,
        movement_type,
        audit_action,
    ):
        """
        Evita repetir la misma lógica en:
        - custody-deliver
        - custody-receive
        """

        context = (
            self.get_serializer_context()
        )

        context[
            "custody_movement_type"
        ] = movement_type

        serializer = self.get_serializer(
            data=request.data,
            context=context,
        )

        serializer.is_valid(
            raise_exception=True
        )

        movement = serializer.save()

        log_event(
            request=request,
            action=audit_action,
            actor=request.user,
            target=movement,
            unit=movement.unit,
            metadata={
                "personnel_tin": (
                    movement.personnel.tin
                ),
                "total_items": (
                    movement.items.count()
                ),
                "reference_document": (
                    movement.reference_document
                ),
                "movement_type": (
                    movement.movement_type
                ),
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # =========================================================
    # ENTREGAR DEL PAÑOL AL PERSONAL
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="custody-deliver",
        url_name="custody-deliver",
    )
    def custody_deliver(
        self,
        request,
    ):
        return self._create_custody_action(
            request=request,
            movement_type=(
                AssignmentCustodyMovementType.DELIVERY
            ),
            audit_action=(
                "INDIVIDUAL_CUSTODY_DELIVERED"
            ),
        )

    # =========================================================
    # RECIBIR DEL PERSONAL EN EL PAÑOL
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="custody-receive",
        url_name="custody-receive",
    )
    def custody_receive(
        self,
        request,
    ):
        return self._create_custody_action(
            request=request,
            movement_type=(
                AssignmentCustodyMovementType.RECEIPT
            ),
            audit_action=(
                "INDIVIDUAL_CUSTODY_RECEIVED"
            ),
        )