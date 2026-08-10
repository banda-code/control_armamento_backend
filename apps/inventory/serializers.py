from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from rest_framework import serializers

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
    UnitOfMeasure,
)


class CleanModelSerializer(serializers.ModelSerializer):
    """
    Ejecuta las validaciones definidas en el método clean()
    de cada modelo antes de guardar.
    """

    def validate(self, attrs):
        instance = self.instance or self.Meta.model()

        for field_name, value in attrs.items():
            setattr(instance, field_name, value)

        try:
            instance.clean()

        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(
                    exc.message_dict
                )

            raise serializers.ValidationError(
                {
                    "detail": exc.messages,
                }
            )

        return attrs


class MaterialCategorySerializer(
    CleanModelSerializer
):
    class Meta:
        model = MaterialCategory
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class MaterialTypeSerializer(
    CleanModelSerializer
):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    control_method_display = serializers.CharField(
        source="get_control_method_display",
        read_only=True,
    )

    class Meta:
        model = MaterialType
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class ManufacturerSerializer(
    CleanModelSerializer
):
    class Meta:
        model = Manufacturer
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class CountrySerializer(
    CleanModelSerializer
):
    class Meta:
        model = Country
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class CaliberSerializer(
    CleanModelSerializer
):
    class Meta:
        model = Caliber
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class UnitOfMeasureSerializer(
    CleanModelSerializer
):
    class Meta:
        model = UnitOfMeasure
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class MaterialSpecificationSerializer(
    CleanModelSerializer
):
    material_type_name = serializers.CharField(
        source="material_type.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="material_type.category.name",
        read_only=True,
    )

    control_method = serializers.CharField(
        source="material_type.control_method",
        read_only=True,
    )

    manufacturer_name = serializers.CharField(
        source="manufacturer.name",
        read_only=True,
        allow_null=True,
    )

    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
        allow_null=True,
    )

    caliber_name = serializers.CharField(
        source="caliber.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = MaterialSpecification
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class ArmorySerializer(
    CleanModelSerializer
):
    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
    )

    class Meta:
        model = Armory
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

        # Desactivamos el mensaje automático de DRF.
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # -------------------------------------------------
        # OBTENER VALORES ACTUALES
        # -------------------------------------------------

        unit = attrs.get(
            "unit",
            getattr(
                self.instance,
                "unit",
                None,
            ),
        )

        name = attrs.get(
            "name",
            getattr(
                self.instance,
                "name",
                "",
            ),
        )

        code = attrs.get(
            "code",
            getattr(
                self.instance,
                "code",
                "",
            ),
        )

        # -------------------------------------------------
        # NORMALIZAR
        # -------------------------------------------------

        if name:
            name = (
                name
                .strip()
                .upper()
            )

            attrs["name"] = name

        if code:
            code = (
                code
                .strip()
                .upper()
            )

            attrs["code"] = code

        # -------------------------------------------------
        # VALIDAR CÓDIGO POR UNIDAD
        # -------------------------------------------------

        if unit and code:
            queryset = (
                Armory.objects.filter(
                    unit=unit,
                    code=code,
                )
            )

            # Al editar, excluir el propio registro.
            if self.instance:
                queryset = (
                    queryset.exclude(
                        pk=self.instance.pk
                    )
                )

            if queryset.exists():
                raise serializers.ValidationError(
                    {
                        "code": (
                            "Ya existe una armería "
                            "o depósito con este "
                            "código en la unidad "
                            "seleccionada."
                        )
                    }
                )

        # -------------------------------------------------
        # VALIDAR NOMBRE POR UNIDAD
        # -------------------------------------------------

        if unit and name:
            queryset = (
                Armory.objects.filter(
                    unit=unit,
                    name=name,
                )
            )

            if self.instance:
                queryset = (
                    queryset.exclude(
                        pk=self.instance.pk
                    )
                )

            if queryset.exists():
                raise serializers.ValidationError(
                    {
                        "name": (
                            "Ya existe una armería "
                            "o depósito con este "
                            "nombre en la unidad "
                            "seleccionada."
                        )
                    }
                )

        return attrs

class SerializedMaterialSerializer(
    CleanModelSerializer
):
    category_name = serializers.CharField(
        source="specification.material_type.category.name",
        read_only=True,
    )

    material_type_name = serializers.CharField(
        source="specification.material_type.name",
        read_only=True,
    )

    specification_name = serializers.CharField(
        source="specification.name",
        read_only=True,
    )

    manufacturer_name = serializers.CharField(
        source="specification.manufacturer.name",
        read_only=True,
        allow_null=True,
    )

    country_name = serializers.CharField(
        source="specification.country.name",
        read_only=True,
        allow_null=True,
    )

    caliber_name = serializers.CharField(
        source="specification.caliber.name",
        read_only=True,
        allow_null=True,
    )

    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
    )

    armory_name = serializers.CharField(
        source="armory.name",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    physical_condition_display = serializers.CharField(
        source="get_physical_condition_display",
        read_only=True,
    )

    class Meta:
        model = SerializedMaterial
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )


class StockMaterialSerializer(
    CleanModelSerializer
):
    specification_name = serializers.CharField(
        source="specification.name",
        read_only=True,
    )

    material_type_name = serializers.CharField(
        source="specification.material_type.name",
        read_only=True,
    )

    unit_of_measure_name = serializers.CharField(
        source="unit_of_measure.name",
        read_only=True,
    )

    unit_of_measure_symbol = serializers.CharField(
        source="unit_of_measure.symbol",
        read_only=True,
    )

    class Meta:
        model = StockMaterial
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class StockBatchSerializer(
    CleanModelSerializer
):
    stock_material_code = serializers.CharField(
        source="stock_material.internal_code",
        read_only=True,
    )

    specification_name = serializers.CharField(
        source="stock_material.specification.name",
        read_only=True,
    )

    unit_of_measure_name = serializers.CharField(
        source="stock_material.unit_of_measure.name",
        read_only=True,
    )

    unit_of_measure_symbol = serializers.CharField(
        source="stock_material.unit_of_measure.symbol",
        read_only=True,
    )

    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
    )

    armory_name = serializers.CharField(
        source="armory.name",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    physical_condition_display = serializers.CharField(
        source="get_physical_condition_display",
        read_only=True,
    )
    class Meta:
        model = StockBatch
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        stock_material = attrs.get(
            "stock_material"
        )

        if (
            stock_material is None
            and self.instance
        ):
            stock_material = (
                self.instance.stock_material
            )

        initial_quantity = attrs.get(
            "initial_quantity"
        )

        if (
            initial_quantity is None
            and self.instance
        ):
            initial_quantity = (
                self.instance.initial_quantity
            )

        current_quantity = attrs.get(
            "current_quantity"
        )

        if (
            current_quantity is None
            and self.instance
        ):
            current_quantity = (
                self.instance.current_quantity
            )

        if stock_material:
            unit_of_measure = (
                stock_material.unit_of_measure
            )

            if not unit_of_measure.allows_decimals:
                quantities = {
                    "initial_quantity": (
                        initial_quantity
                    ),
                    "current_quantity": (
                        current_quantity
                    ),
                }

                errors = {}

                for field_name, value in (
                    quantities.items()
                ):
                    if (
                        value is not None
                        and value
                        != value.to_integral_value()
                    ):
                        errors[field_name] = (
                            "Esta unidad de medida "
                            "no permite cantidades "
                            "decimales."
                        )

                if errors:
                    raise serializers.ValidationError(
                        errors
                    )

        return attrs


class ComponentTypeSerializer(
    CleanModelSerializer
):
    class Meta:
        model = ComponentType
        fields = "__all__"

        # La unicidad la controlaremos nosotros
        # para poder comparar sin importar
        # mayúsculas/minúsculas.
        extra_kwargs = {
            "name": {
                "validators": [],
            }
        }

    def validate(self, attrs):
        name = attrs.get(
            "name",
            getattr(
                self.instance,
                "name",
                "",
            ),
        )

        # -----------------------------------------
        # NORMALIZAR NOMBRE
        # -----------------------------------------

        if name:
            name = (
                name
                .strip()
                .upper()
            )

            attrs["name"] = name

            # -------------------------------------
            # EVITAR DUPLICADOS
            # -------------------------------------

            queryset = (
                ComponentType.objects.filter(
                    name__iexact=name
                )
            )

            # Si estamos editando,
            # no comparar contra sí mismo.
            if self.instance:
                queryset = (
                    queryset.exclude(
                        pk=self.instance.pk
                    )
                )

            if queryset.exists():
                raise serializers.ValidationError(
                    {
                        "name": (
                            "Ya existe un tipo de "
                            "componente o accesorio "
                            "con este nombre."
                        )
                    }
                )

        return super().validate(attrs)


class SerializedMaterialComponentSerializer(
    CleanModelSerializer
):
    material_code = serializers.CharField(
        source="material.institutional_code",
        read_only=True,
    )

    material_identification_number = serializers.CharField(
        source="material.identification_number",
        read_only=True,
    )

    component_type_name = serializers.CharField(
        source="component_type.name",
        read_only=True,
    )

    component_is_serialized = serializers.BooleanField(
        source="component_type.is_serialized",
        read_only=True,
    )

    unit_name = serializers.CharField(
        source="material.unit.name",
        read_only=True,
    )

    class Meta:
        model = SerializedMaterialComponent
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )