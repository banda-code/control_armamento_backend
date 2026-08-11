from rest_framework import (
    filters,
    viewsets,
)
from apps.accounts.scopes import (
    get_user_unit_id,
)
from rest_framework.exceptions import (
    PermissionDenied,
)

from apps.inventory.models import (
    Armory,
    Caliber,
    ComponentType,
    Country,
    Manufacturer,
    MaterialCategory,
    MaterialSpecification,
    MaterialType,
    SerializedMaterial,
    SerializedMaterialComponent,
    StockBatch,
    StockMaterial,
    StockMovement,
    UnitOfMeasure,
)
from apps.inventory.permissions import (
    ADMINISTRATOR,
    NAVY_COMMAND,
    CatalogPermission,
    UnitInventoryPermission,
    get_user_role,
    user_can_write_unit,
)
from apps.inventory.serializers import (
    ArmorySerializer,
    CaliberSerializer,
    ComponentTypeSerializer,
    CountrySerializer,
    ManufacturerSerializer,
    MaterialCategorySerializer,
    MaterialSpecificationSerializer,
    MaterialTypeSerializer,
    SerializedMaterialComponentSerializer,
    SerializedMaterialSerializer,
    StockBatchSerializer,
    StockMaterialSerializer,
    StockMovementSerializer,
    UnitOfMeasureSerializer,
)


class SoftDeleteMixin:
    """
    DELETE desactiva el registro en lugar
    de eliminarlo físicamente.
    """

    def perform_destroy(self, instance):
        field_names = {
            field.name
            for field in instance._meta.fields
        }

        if "is_active" not in field_names:
            instance.delete()
            return

        instance.is_active = False
        update_fields = ["is_active"]

        if "updated_by" in field_names:
            instance.updated_by = (
                self.request.user
            )
            update_fields.append(
                "updated_by"
            )

        if "updated_at" in field_names:
            update_fields.append(
                "updated_at"
            )

        instance.save(
            update_fields=update_fields
        )


class CatalogViewSet(
    SoftDeleteMixin,
    viewsets.ModelViewSet,
):
    permission_classes = [
        CatalogPermission,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]


class UnitScopedViewSet(
    SoftDeleteMixin,
    viewsets.ModelViewSet,
):
    permission_classes = [
        UnitInventoryPermission,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    unit_lookup = "unit_id"

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user
        role = get_user_role(user)

        if role in {
            ADMINISTRATOR,
            NAVY_COMMAND,
        }:
            return queryset

        unit_id = get_user_unit_id(user)

        if not unit_id:
            return queryset.none()

        return queryset.filter(
            **{
                self.unit_lookup: unit_id,
            }
        )

    def ensure_unit_write_access(
        self,
        unit_id,
    ):
        if not user_can_write_unit(
            self.request.user,
            unit_id,
        ):
            raise PermissionDenied(
                "No puede modificar registros "
                "de otra unidad."
            )


class MaterialCategoryViewSet(
    CatalogViewSet
):
    queryset = MaterialCategory.objects.all()

    serializer_class = (
        MaterialCategorySerializer
    )

    search_fields = [
        "name",
        "code",
        "description",
    ]

    ordering_fields = [
        "name",
        "code",
        "created_at",
    ]


class MaterialTypeViewSet(
    CatalogViewSet
):
    queryset = (
        MaterialType.objects.select_related(
            "category",
        ).all()
    )

    serializer_class = MaterialTypeSerializer

    search_fields = [
        "name",
        "code",
        "category__name",
    ]

    ordering_fields = [
        "name",
        "code",
        "created_at",
    ]


class ManufacturerViewSet(
    CatalogViewSet
):
    queryset = Manufacturer.objects.all()

    serializer_class = ManufacturerSerializer

    search_fields = [
        "name",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]


class CountryViewSet(
    CatalogViewSet
):
    queryset = Country.objects.all()

    serializer_class = CountrySerializer

    search_fields = [
        "name",
        "code",
    ]

    ordering_fields = [
        "name",
        "code",
        "created_at",
    ]


class CaliberViewSet(
    CatalogViewSet
):
    queryset = Caliber.objects.all()

    serializer_class = CaliberSerializer

    search_fields = [
        "name",
        "description",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]


class UnitOfMeasureViewSet(
    CatalogViewSet
):
    queryset = UnitOfMeasure.objects.all()

    serializer_class = (
        UnitOfMeasureSerializer
    )

    search_fields = [
        "name",
        "symbol",
    ]

    ordering_fields = [
        "name",
        "symbol",
        "created_at",
    ]


class MaterialSpecificationViewSet(
    CatalogViewSet
):
    queryset = (
        MaterialSpecification.objects
        .select_related(
            "material_type",
            "material_type__category",
            "manufacturer",
            "country",
            "caliber",
        )
        .all()
    )

    serializer_class = (
        MaterialSpecificationSerializer
    )

    search_fields = [
        "name",
        "material_type__name",
        "material_type__category__name",
        "manufacturer__name",
        "country__name",
        "caliber__name",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]


class StockMaterialViewSet(
    CatalogViewSet
):
    queryset = (
        StockMaterial.objects.select_related(
            "specification",
            "specification__material_type",
            "unit_of_measure",
        ).all()
    )

    serializer_class = StockMaterialSerializer

    search_fields = [
        "internal_code",
        "specification__name",
        "specification__material_type__name",
        "unit_of_measure__name",
    ]

    ordering_fields = [
        "internal_code",
        "minimum_stock",
        "created_at",
    ]


class ComponentTypeViewSet(
    CatalogViewSet
):
    queryset = ComponentType.objects.all()

    serializer_class = (
        ComponentTypeSerializer
    )

    search_fields = [
        "name",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]


class ArmoryViewSet(
    UnitScopedViewSet
):
    queryset = Armory.objects.select_related(
        "unit",
    ).all()

    serializer_class = ArmorySerializer

    search_fields = [
        "name",
        "code",
        "unit__name",
        "description",
    ]

    ordering_fields = [
        "name",
        "code",
        "created_at",
    ]

    def perform_create(self, serializer):
        unit = serializer.validated_data[
            "unit"
        ]

        self.ensure_unit_write_access(
            unit.id
        )

        serializer.save()

    def perform_update(self, serializer):
        unit = serializer.validated_data.get(
            "unit",
            serializer.instance.unit,
        )

        self.ensure_unit_write_access(
            unit.id
        )

        serializer.save()


class SerializedMaterialViewSet(
    UnitScopedViewSet
):
    queryset = (
        SerializedMaterial.objects
        .select_related(
            "specification",
            "specification__material_type",
            "specification__manufacturer",
            "specification__country",
            "specification__caliber",
            "unit",
            "armory",
            "created_by",
            "updated_by",
        )
        .all()
    )

    serializer_class = (
        SerializedMaterialSerializer
    )

    search_fields = [
        "institutional_code",
        "identification_number",
        "specification__name",
        "specification__material_type__name",
        "specification__manufacturer__name",
        "unit__name",
        "armory__name",
        "observations",
    ]

    ordering_fields = [
        "institutional_code",
        "identification_number",
        "status",
        "physical_condition",
        "created_at",
    ]

    def perform_create(self, serializer):
        unit = serializer.validated_data[
            "unit"
        ]

        self.ensure_unit_write_access(
            unit.id
        )

        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        unit = serializer.validated_data.get(
            "unit",
            serializer.instance.unit,
        )

        self.ensure_unit_write_access(
            unit.id
        )

        serializer.save(
            updated_by=self.request.user,
        )


class StockBatchViewSet(
    UnitScopedViewSet
):
    queryset = (
        StockBatch.objects.select_related(
            "stock_material",
            "stock_material__specification",
            (
                "stock_material__"
                "specification__material_type"
            ),
            "stock_material__unit_of_measure",
            "unit",
            "armory",
            "created_by",
            "updated_by",
        ).all()
    )

    serializer_class = StockBatchSerializer

    search_fields = [
        "stock_material__internal_code",
        "stock_material__specification__name",
        "lot_number",
        "unit__name",
        "armory__name",
        "observations",
    ]

    ordering_fields = [
        "lot_number",
        "current_quantity",
        "status",
        "expiration_date",
        "created_at",
    ]

    # =====================================================
    # FILTROS
    # =====================================================

    def get_queryset(self):
        queryset = super().get_queryset()

        stock_material_id = (
            self.request.query_params.get(
                "stock_material"
            )
        )

        unit_id = (
            self.request.query_params.get(
                "unit"
            )
        )

        armory_id = (
            self.request.query_params.get(
                "armory"
            )
        )

        status_value = (
            self.request.query_params.get(
                "status"
            )
        )

        is_active = (
            self.request.query_params.get(
                "is_active"
            )
        )

        if stock_material_id:
            queryset = queryset.filter(
                stock_material_id=
                stock_material_id
            )

        if unit_id:
            queryset = queryset.filter(
                unit_id=unit_id
            )

        if armory_id:
            queryset = queryset.filter(
                armory_id=armory_id
            )

        if status_value:
            queryset = queryset.filter(
                status=status_value
            )

        if is_active in (
            "true",
            "false",
        ):
            queryset = queryset.filter(
                is_active=(
                    is_active == "true"
                )
            )

        return queryset

    # =====================================================
    # CREAR
    # =====================================================

    def perform_create(
        self,
        serializer,
    ):
        unit = (
            serializer.validated_data[
                "unit"
            ]
        )

        self.ensure_unit_write_access(
            unit.id
        )

        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    def perform_update(
        self,
        serializer,
    ):
        unit = (
            serializer.validated_data.get(
                "unit",
                serializer.instance.unit,
            )
        )

        self.ensure_unit_write_access(
            unit.id
        )

        serializer.save(
            updated_by=self.request.user,
        )


# =========================================================
# MOVIMIENTOS DE EXISTENCIAS
# =========================================================


class StockMovementViewSet(
    UnitScopedViewSet
):
    queryset = (
        StockMovement.objects
        .select_related(
            "batch",
            "batch__stock_material",
            (
                "batch__stock_material__"
                "specification"
            ),
            (
                "batch__stock_material__"
                "unit_of_measure"
            ),
            "unit",
            "armory",
            "created_by",
        )
        .all()
    )

    serializer_class = (
        StockMovementSerializer
    )

    # Los movimientos son registros históricos:
    # se pueden consultar y crear,
    # pero NO modificar ni eliminar.
    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    search_fields = [
        "batch__lot_number",
        (
            "batch__stock_material__"
            "internal_code"
        ),
        (
            "batch__stock_material__"
            "specification__name"
        ),
        "unit__name",
        "armory__name",
        "reason",
        "reference_document",
        "observations",
    ]

    ordering_fields = [
        "created_at",
        "movement_type",
        "quantity",
        "previous_quantity",
        "new_quantity",
    ]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
        )

        batch_id = (
            self.request
            .query_params
            .get("batch")
        )

        movement_type = (
            self.request
            .query_params
            .get("movement_type")
        )

        unit_id = (
            self.request
            .query_params
            .get("unit")
        )

        armory_id = (
            self.request
            .query_params
            .get("armory")
        )

        if batch_id:
            queryset = queryset.filter(
                batch_id=batch_id
            )

        if movement_type:
            queryset = queryset.filter(
                movement_type=
                    movement_type
            )

        if unit_id:
            queryset = queryset.filter(
                unit_id=unit_id
            )

        if armory_id:
            queryset = queryset.filter(
                armory_id=armory_id
            )

        return queryset

    def perform_create(
        self,
        serializer,
    ):
        batch = (
            serializer.validated_data[
                "batch"
            ]
        )

        # Verifica que el usuario tenga permiso
        # de escritura sobre la unidad del lote.
        self.ensure_unit_write_access(
            batch.unit_id
        )

        serializer.save(
            created_by=
                self.request.user
        )

class SerializedMaterialComponentViewSet(
    UnitScopedViewSet
):
    queryset = (
        SerializedMaterialComponent.objects
        .select_related(
            "material",
            "material__unit",
            "component_type",
        )
        .all()
    )

    serializer_class = (
        SerializedMaterialComponentSerializer
    )

    unit_lookup = "material__unit_id"

    search_fields = [
        "material__institutional_code",
        "material__identification_number",
        "component_type__name",
        "identification_number",
        "observations",
    ]

    ordering_fields = [
        "quantity",
        "created_at",
    ]
    def get_queryset(self):
        queryset = super().get_queryset()

        material_id = self.request.query_params.get("material")
        is_active = self.request.query_params.get("is_active")

        if material_id:
            queryset = queryset.filter(
                material_id=material_id
            )

        if is_active in ("true", "false"):
            queryset = queryset.filter(
                is_active=(is_active == "true")
            )

        return queryset

    def perform_create(self, serializer):
        material = serializer.validated_data[
            "material"
        ]

        self.ensure_unit_write_access(
            material.unit_id
        )

        serializer.save()

    def perform_update(self, serializer):
        material = (
            serializer.validated_data.get(
                "material",
                serializer.instance.material,
            )
        )

        self.ensure_unit_write_access(
            material.unit_id
        )

        serializer.save()