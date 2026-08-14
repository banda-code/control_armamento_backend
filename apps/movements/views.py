from rest_framework import (
    filters,
    mixins,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.scopes import get_user_unit_id
from apps.audit.utils import log_event

from .models import (
    SerializedMovement,
    SerializedMovementItem,
    SerializedMovementType,
)
from .permissions import SerializedMovementPermission
from .serializers import (
    OutstandingSerializedMaterialSerializer,
    SerializedMovementOutSerializer,
    SerializedMovementReturnSerializer,
    SerializedMovementSerializer,
)


class SerializedMovementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Movimientos de materiales serializados
    de dotación de unidad.

    Permite:
    - consultar movimientos,
    - consultar detalle,
    - registrar salidas,
    - registrar retornos.

    No permite:
    - crear movimientos genéricos,
    - editar movimientos,
    - eliminar movimientos.
    """

    queryset = (
        SerializedMovement.objects
        .select_related(
            "responsible_personnel",
            "responsible_personnel__rank",
            "responsible_personnel__position",
            "unit",
            "armory",
            "created_by",
        )
        .prefetch_related(
            "items__material",
            "items__material__specification",
            "items__source_item",
        )
        .all()
    )

    permission_classes = [
        SerializedMovementPermission,
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
        "responsible_personnel__tin",
        "responsible_personnel__first_name",
        "responsible_personnel__paternal_last_name",
        "responsible_personnel__maternal_last_name",
        "unit__name",
        "armory__name",
        "reason",
        "reference_document",
        "items__material__institutional_code",
        "items__material__identification_number",
        "items__material__specification__name",
    ]

    ordering_fields = [
        "movement_at",
        "created_at",
        "updated_at",
        "movement_type",
    ]

    ordering = [
        "-movement_at",
    ]

    # ========================================================
    # SERIALIZER SEGÚN OPERACIÓN
    # ========================================================

    def get_serializer_class(self):
        if self.action == "out":
            return SerializedMovementOutSerializer

        if self.action == "return_materials":
            return SerializedMovementReturnSerializer

        if self.action == "currently_out":
            return OutstandingSerializedMaterialSerializer

        return SerializedMovementSerializer

    # ========================================================
    # ALCANCE POR UNIDAD
    # ========================================================

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

        # Administrador y Comando:
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
                unit_id=user_unit_id
            )

        # ----------------------------------------------------
        # Filtros opcionales
        # ----------------------------------------------------

        movement_type = (
            self.request.query_params.get(
                "movement_type"
            )
        )

        responsible_personnel = (
            self.request.query_params.get(
                "responsible_personnel"
            )
        )

        material = (
            self.request.query_params.get(
                "material"
            )
        )

        unit = (
            self.request.query_params.get(
                "unit"
            )
        )

        if movement_type:
            scoped_queryset = (
                scoped_queryset.filter(
                    movement_type=movement_type
                )
            )

        if responsible_personnel:
            scoped_queryset = (
                scoped_queryset.filter(
                    responsible_personnel_id=(
                        responsible_personnel
                    )
                )
            )

        if material:
            scoped_queryset = (
                scoped_queryset.filter(
                    items__material_id=material
                )
            )

        # Solo usuarios globales pueden
        # consultar expresamente otra unidad.
        if (
            unit
            and user.has_global_scope
        ):
            scoped_queryset = (
                scoped_queryset.filter(
                    unit_id=unit
                )
            )

        return scoped_queryset.distinct()

    # ========================================================
    # VALIDAR UNIDAD DEL USUARIO
    # ========================================================

    def _validate_user_unit(
        self,
        unit,
    ):
        """
        Impide que un usuario con alcance de unidad
        registre movimientos para otra unidad.
        """

        user = self.request.user

        if user.has_global_scope:
            return

        user_unit_id = get_user_unit_id(
            user
        )

        if not user_unit_id:
            raise PermissionDenied(
                "El usuario no tiene una unidad "
                "institucional asociada."
            )

        if (
            str(user_unit_id)
            != str(unit.id)
        ):
            raise PermissionDenied(
                "No puede registrar movimientos "
                "para otra unidad."
            )


    # ========================================================
    # MATERIALES ACTUALMENTE AFUERA
    # ========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="currently-out",
        url_name="currently-out",
    )
    def currently_out(
        self,
        request,
    ):
        """
        Devuelve materiales serializados de dotación
        de unidad que tienen una SALIDA registrada
        y todavía no poseen RETORNO.

        Es decir:
            OUT
            +
            sin return_item
            =
            material actualmente afuera.
        """

        user = request.user

        queryset = (
            SerializedMovementItem.objects
            .select_related(
                "material",
                "material__specification",
                "movement",
                "movement__responsible_personnel",
                "movement__responsible_personnel__rank",
                "movement__unit",
                "movement__armory",
                "movement__created_by",
            )
            .filter(
                movement__movement_type=(
                    SerializedMovementType.OUT
                ),
                return_items__isnull=True,
            )
            .order_by(
                "-movement__movement_at",
                "material__institutional_code",
            )
        )

        # ----------------------------------------------------
        # ALCANCE INSTITUCIONAL
        # ----------------------------------------------------

        if not user.has_global_scope:
            user_unit_id = get_user_unit_id(
                user
            )

            if not user_unit_id:
                queryset = queryset.none()

            else:
                queryset = queryset.filter(
                    movement__unit_id=(
                        user_unit_id
                    )
                )

        # ----------------------------------------------------
        # FILTROS OPCIONALES
        # ----------------------------------------------------

        responsible_personnel = (
            request.query_params.get(
                "responsible_personnel"
            )
        )

        material = (
            request.query_params.get(
                "material"
            )
        )

        armory = (
            request.query_params.get(
                "armory"
            )
        )

        unit = (
            request.query_params.get(
                "unit"
            )
        )

        if responsible_personnel:
            queryset = queryset.filter(
                movement__responsible_personnel_id=(
                    responsible_personnel
                )
            )

        if material:
            queryset = queryset.filter(
                material_id=material
            )

        if armory:
            queryset = queryset.filter(
                movement__armory_id=armory
            )

        # Solamente usuarios con alcance global
        # pueden consultar expresamente otra unidad.
        if (
            unit
            and user.has_global_scope
        ):
            queryset = queryset.filter(
                movement__unit_id=unit
            )

        # ----------------------------------------------------
        # PAGINACIÓN
        # ----------------------------------------------------

        page = self.paginate_queryset(
            queryset
        )

        if page is not None:
            serializer = (
                OutstandingSerializedMaterialSerializer(
                    page,
                    many=True,
                    context=self.get_serializer_context(),
                )
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = (
            OutstandingSerializedMaterialSerializer(
                queryset,
                many=True,
                context=self.get_serializer_context(),
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # SALIDA
    # ========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="out",
        url_name="out",
    )
    def out(
        self,
        request,
    ):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        # Unidad ya convertida en objeto
        # después de is_valid().
        unit = serializer.validated_data[
            "unit"
        ]

        self._validate_user_unit(
            unit
        )

        movement = serializer.save()

        log_event(
            request=request,
            action=(
                "SERIALIZED_MATERIAL_OUT"
            ),
            actor=request.user,
            target=movement,
            unit=movement.unit,
            metadata={
                "movement_type": (
                    movement.movement_type
                ),
                "responsible_tin": (
                    movement
                    .responsible_personnel
                    .tin
                ),
                "total_items": (
                    movement.items.count()
                ),
                "reference_document": (
                    movement.reference_document
                ),
                "material_codes": [
                    item.material.institutional_code
                    for item in (
                        movement.items
                        .select_related(
                            "material"
                        )
                        .all()
                    )
                ],
            },
        )

        response_serializer = (
            SerializedMovementSerializer(
                movement,
                context=self.get_serializer_context(),
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # ========================================================
    # RETORNO
    # ========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="return",
        url_name="return",
    )
    def return_materials(
        self,
        request,
    ):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        unit = serializer.validated_data[
            "unit"
        ]

        self._validate_user_unit(
            unit
        )

        movement = serializer.save()

        log_event(
            request=request,
            action=(
                "SERIALIZED_MATERIAL_RETURN"
            ),
            actor=request.user,
            target=movement,
            unit=movement.unit,
            metadata={
                "movement_type": (
                    movement.movement_type
                ),
                "responsible_tin": (
                    movement
                    .responsible_personnel
                    .tin
                ),
                "total_items": (
                    movement.items.count()
                ),
                "reference_document": (
                    movement.reference_document
                ),
                "material_codes": [
                    item.material.institutional_code
                    for item in (
                        movement.items
                        .select_related(
                            "material"
                        )
                        .all()
                    )
                ],
            },
        )

        response_serializer = (
            SerializedMovementSerializer(
                movement,
                context=self.get_serializer_context(),
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )