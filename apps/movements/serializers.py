from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)

from rest_framework import serializers

from apps.inventory.models import (
    AllocationType,
    Armory,
    SerializedMaterial,
)
from apps.personnel.models import Personnel

from .models import (
    SerializedMovement,
    SerializedMovementItem,
    SerializedMovementType,
)
from .services import (
    create_out_movement,
    create_return_movement,
)


def raise_drf_validation_error(exc):
    """
    Convierte ValidationError de Django
    en ValidationError de DRF.
    """

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(
            exc.message_dict
        )

    raise serializers.ValidationError(
        {
            "non_field_errors": list(
                exc.messages
            )
        }
    )


# ============================================================
# ITEM DE MOVIMIENTO - CONSULTA
# ============================================================


class SerializedMovementItemSerializer(
    serializers.ModelSerializer
):
    material_code = serializers.CharField(
        source="material.institutional_code",
        read_only=True,
    )

    material_identification_number = serializers.CharField(
        source="material.identification_number",
        read_only=True,
    )

    material_specification = serializers.CharField(
        source="material.specification.name",
        read_only=True,
    )

    material_status = serializers.CharField(
        source="material.status",
        read_only=True,
    )

    source_item_id = serializers.UUIDField(
        source="source_item.id",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = SerializedMovementItem

        fields = [
            "id",
            "material",
            "material_code",
            "material_identification_number",
            "material_specification",
            "material_status",
            "source_item_id",
            "observations",
            "created_at",
        ]

        read_only_fields = fields


# ============================================================
# MOVIMIENTO - CONSULTA
# ============================================================


class SerializedMovementSerializer(
    serializers.ModelSerializer
):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )

    responsible_personnel_tin = serializers.CharField(
        source="responsible_personnel.tin",
        read_only=True,
    )

    responsible_personnel_name = serializers.CharField(
        source="responsible_personnel.full_name",
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

    created_by_email = serializers.CharField(
        source="created_by.email",
        read_only=True,
    )

    items = SerializedMovementItemSerializer(
        many=True,
        read_only=True,
    )

    total_items = serializers.SerializerMethodField()

    class Meta:
        model = SerializedMovement

        fields = [
            "id",

            "movement_type",
            "movement_type_display",
            "movement_at",

            "responsible_personnel",
            "responsible_personnel_tin",
            "responsible_personnel_name",

            "unit",
            "unit_name",

            "armory",
            "armory_name",

            "reason",
            "reference_document",
            "observations",

            "items",
            "total_items",

            "created_by",
            "created_by_email",

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_total_items(self, obj):
        return obj.items.count()


# ============================================================
# SALIDA
# ============================================================


class SerializedMovementOutSerializer(
    serializers.Serializer
):
    responsible_personnel = (
        serializers.PrimaryKeyRelatedField(
            queryset=Personnel.objects.filter(
                is_active=True
            )
        )
    )

    unit = serializers.PrimaryKeyRelatedField(
        queryset=(
            Personnel._meta
            .get_field("unit")
            .remote_field.model.objects.all()
        )
    )

    armory = serializers.PrimaryKeyRelatedField(
        queryset=Armory.objects.all()
    )

    materials = serializers.PrimaryKeyRelatedField(
        queryset=SerializedMaterial.objects.filter(
            is_active=True,
            allocation_type=AllocationType.UNIT,
        ),
        many=True,
    )

    reason = serializers.CharField(
        max_length=250,
    )

    reference_document = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        default="",
    )

    observations = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_materials(
        self,
        materials,
    ):
        if not materials:
            raise serializers.ValidationError(
                "Debe seleccionar al menos un material."
            )

        ids = [
            str(material.id)
            for material in materials
        ]

        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "No puede registrar dos veces "
                "el mismo material."
            )

        return materials

    def create(self, validated_data):
        request = self.context[
            "request"
        ]

        materials = validated_data.pop(
            "materials"
        )

        try:
            return create_out_movement(
                actor=request.user,
                responsible_personnel=(
                    validated_data[
                        "responsible_personnel"
                    ]
                ),
                unit=validated_data["unit"],
                armory=validated_data["armory"],
                material_ids=[
                    material.id
                    for material in materials
                ],
                reason=validated_data["reason"],
                reference_document=(
                    validated_data.get(
                        "reference_document",
                        "",
                    )
                ),
                observations=(
                    validated_data.get(
                        "observations",
                        "",
                    )
                ),
            )

        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

    def to_representation(
        self,
        instance,
    ):
        return SerializedMovementSerializer(
            instance,
            context=self.context,
        ).data


# ============================================================
# RETORNO
# ============================================================


class SerializedMovementReturnSerializer(
    serializers.Serializer
):
    responsible_personnel = (
        serializers.PrimaryKeyRelatedField(
            queryset=Personnel.objects.filter(
                is_active=True
            )
        )
    )

    unit = serializers.PrimaryKeyRelatedField(
        queryset=(
            Personnel._meta
            .get_field("unit")
            .remote_field.model.objects.all()
        )
    )

    armory = serializers.PrimaryKeyRelatedField(
        queryset=Armory.objects.all()
    )

    source_items = serializers.PrimaryKeyRelatedField(
        queryset=SerializedMovementItem.objects.filter(
            movement__movement_type=(
                SerializedMovementType.OUT
            ),
            return_items__isnull=True,
        ).select_related(
            "movement",
            "material",
        ),
        many=True,
    )

    reason = serializers.CharField(
        max_length=250,
    )

    reference_document = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        default="",
    )

    observations = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_source_items(
        self,
        source_items,
    ):
        if not source_items:
            raise serializers.ValidationError(
                "Debe seleccionar al menos "
                "un material para retornar."
            )

        ids = [
            str(item.id)
            for item in source_items
        ]

        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "No puede registrar dos veces "
                "el mismo registro de salida."
            )

        return source_items

    def create(self, validated_data):
        request = self.context[
            "request"
        ]

        source_items = validated_data.pop(
            "source_items"
        )

        try:
            return create_return_movement(
                actor=request.user,
                responsible_personnel=(
                    validated_data[
                        "responsible_personnel"
                    ]
                ),
                unit=validated_data["unit"],
                armory=validated_data["armory"],
                source_item_ids=[
                    item.id
                    for item in source_items
                ],
                reason=validated_data["reason"],
                reference_document=(
                    validated_data.get(
                        "reference_document",
                        "",
                    )
                ),
                observations=(
                    validated_data.get(
                        "observations",
                        "",
                    )
                ),
            )

        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

    def to_representation(
        self,
        instance,
    ):
        return SerializedMovementSerializer(
            instance,
            context=self.context,
        ).data


# ============================================================
# MATERIAL ACTUALMENTE AFUERA
# ============================================================


class OutstandingSerializedMaterialSerializer(
    serializers.ModelSerializer
):
    material_code = serializers.CharField(
        source="material.institutional_code",
        read_only=True,
    )

    material_identification_number = serializers.CharField(
        source="material.identification_number",
        read_only=True,
    )

    material_specification = serializers.CharField(
        source="material.specification.name",
        read_only=True,
    )

    material_status = serializers.CharField(
        source="material.status",
        read_only=True,
    )

    movement_id = serializers.UUIDField(
        source="movement.id",
        read_only=True,
    )

    movement_at = serializers.DateTimeField(
        source="movement.movement_at",
        read_only=True,
    )

    responsible_personnel = serializers.UUIDField(
        source="movement.responsible_personnel_id",
        read_only=True,
    )

    responsible_personnel_tin = serializers.CharField(
        source="movement.responsible_personnel.tin",
        read_only=True,
    )

    responsible_personnel_name = serializers.CharField(
        source="movement.responsible_personnel.full_name",
        read_only=True,
    )

    unit = serializers.UUIDField(
        source="movement.unit_id",
        read_only=True,
    )

    unit_name = serializers.CharField(
        source="movement.unit.name",
        read_only=True,
    )

    armory = serializers.UUIDField(
        source="movement.armory_id",
        read_only=True,
    )

    armory_name = serializers.CharField(
        source="movement.armory.name",
        read_only=True,
    )

    reason = serializers.CharField(
        source="movement.reason",
        read_only=True,
    )

    reference_document = serializers.CharField(
        source="movement.reference_document",
        read_only=True,
    )

    movement_observations = serializers.CharField(
        source="movement.observations",
        read_only=True,
    )

    class Meta:
        model = SerializedMovementItem

        fields = [
            "id",

            # Material
            "material",
            "material_code",
            "material_identification_number",
            "material_specification",
            "material_status",

            # Salida
            "movement_id",
            "movement_at",

            # Responsable temporal
            "responsible_personnel",
            "responsible_personnel_tin",
            "responsible_personnel_name",

            # Dependencia
            "unit",
            "unit_name",
            "armory",
            "armory_name",

            # Motivo y respaldo
            "reason",
            "reference_document",
            "movement_observations",

            # Observación específica del item
            "observations",

            "created_at",
        ]

        read_only_fields = fields