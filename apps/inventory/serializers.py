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
    class Meta:
        model = Armory
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class SerializedMaterialSerializer(
    CleanModelSerializer
):
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

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class SerializedMaterialComponentSerializer(
    CleanModelSerializer
):
    class Meta:
        model = SerializedMaterialComponent
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )