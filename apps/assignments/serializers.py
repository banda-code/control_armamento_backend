from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from apps.accounts.scopes import get_user_unit_id
from apps.inventory.models import (
    SerializedMaterial,
    SerializedMaterialComponent,
    SerializedStatus,
)
from apps.personnel.models import Personnel

from .models import (
    AssignmentStatus,
    IndividualAssignment,
    IndividualAssignmentComponent,
)


def raise_drf_validation_error(exc):
    """
    Convierte errores de validación de Django
    en errores de Django REST Framework.
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
# COMPONENTES - CONSULTA
# ============================================================


class IndividualAssignmentComponentSerializer(
    serializers.ModelSerializer
):
    component_type = serializers.CharField(
        source="component.component_type.name",
        read_only=True,
    )

    identification_number = serializers.CharField(
        source="component.identification_number",
        read_only=True,
        allow_null=True,
    )

    available_quantity = serializers.IntegerField(
        source="component.quantity",
        read_only=True,
    )

    class Meta:
        model = IndividualAssignmentComponent

        fields = [
            "id",
            "component",
            "component_type",
            "identification_number",
            "available_quantity",
            "quantity_delivered",
            "observations",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


# ============================================================
# COMPONENTES - ENTRADA
# ============================================================


class AssignmentComponentInputSerializer(
    serializers.Serializer
):
    component = serializers.PrimaryKeyRelatedField(
        queryset=SerializedMaterialComponent.objects.filter(
            is_active=True
        ).select_related(
            "material",
            "component_type",
        )
    )

    quantity_delivered = serializers.IntegerField(
        min_value=1,
        default=1,
    )

    observations = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


# ============================================================
# DOTACIÓN - CONSULTA
# ============================================================


class IndividualAssignmentSerializer(
    serializers.ModelSerializer
):
    personnel_tin = serializers.CharField(
        source="personnel.tin",
        read_only=True,
    )

    personnel_name = serializers.CharField(
        source="personnel.full_name",
        read_only=True,
    )

    personnel_unit = serializers.UUIDField(
        source="personnel.unit_id",
        read_only=True,
        allow_null=True,
    )

    personnel_unit_name = serializers.CharField(
        source="personnel.unit.name",
        read_only=True,
        default=None,
    )

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

    material_unit = serializers.UUIDField(
        source="material.unit_id",
        read_only=True,
    )

    material_unit_name = serializers.CharField(
        source="material.unit.name",
        read_only=True,
    )

    material_status = serializers.CharField(
        source="material.status",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    assigned_by_email = serializers.CharField(
        source="assigned_by.email",
        read_only=True,
    )

    returned_by_email = serializers.CharField(
        source="returned_by.email",
        read_only=True,
        default=None,
    )

    components = IndividualAssignmentComponentSerializer(
        source="assigned_components",
        many=True,
        read_only=True,
    )

    class Meta:
        model = IndividualAssignment

        fields = [
            "id",

            # Personal
            "personnel",
            "personnel_tin",
            "personnel_name",
            "personnel_unit",
            "personnel_unit_name",

            # Material
            "material",
            "material_code",
            "material_identification_number",
            "material_specification",
            "material_unit",
            "material_unit_name",
            "material_status",

            # Entrega
            "assigned_at",
            "assignment_document",
            "assignment_observations",
            "assigned_by",
            "assigned_by_email",

            # Estado
            "status",
            "status_display",

            # Devolución
            "returned_at",
            "return_document",
            "return_observations",
            "returned_by",
            "returned_by_email",

            # Componentes
            "components",

            # Auditoría temporal
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


# ============================================================
# CREACIÓN DE DOTACIÓN
# ============================================================


class IndividualAssignmentCreateSerializer(
    serializers.Serializer
):
    personnel = serializers.PrimaryKeyRelatedField(
        queryset=Personnel.objects.filter(
            is_active=True
        ).select_related(
            "unit",
        )
    )

    material = serializers.PrimaryKeyRelatedField(
        queryset=SerializedMaterial.objects.filter(
            is_active=True
        ).select_related(
            "unit",
            "armory",
            "specification",
            "specification__material_type",
        )
    )

    assignment_document = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        default="",
    )

    assignment_observations = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    components = AssignmentComponentInputSerializer(
        many=True,
        required=False,
        default=list,
    )

    def validate(self, attrs):
        personnel = attrs["personnel"]
        material = attrs["material"]
        components = attrs.get(
            "components",
            [],
        )

        request = self.context.get(
            "request"
        )

        # -----------------------------------------------------
        # Unidad del personal
        # -----------------------------------------------------

        if not personnel.unit_id:
            raise serializers.ValidationError(
                {
                    "personnel": (
                        "El personal debe estar asociado "
                        "a una unidad."
                    )
                }
            )

        # -----------------------------------------------------
        # Misma unidad
        # -----------------------------------------------------

        if (
            personnel.unit_id
            != material.unit_id
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material y el personal "
                        "deben pertenecer a la misma unidad."
                    )
                }
            )

        # -----------------------------------------------------
        # Alcance del usuario que registra
        # -----------------------------------------------------

        if (
            request
            and request.user
            and request.user.is_authenticated
            and not request.user.has_global_scope
        ):
            user_unit_id = get_user_unit_id(
                request.user
            )

            if not user_unit_id:
                raise serializers.ValidationError(
                    {
                        "personnel": (
                            "El usuario no tiene una unidad "
                            "institucional asociada."
                        )
                    }
                )

            if (
                str(user_unit_id)
                != str(personnel.unit_id)
            ):
                raise serializers.ValidationError(
                    {
                        "personnel": (
                            "No puede registrar dotaciones "
                            "para otra unidad."
                        )
                    }
                )

        # -----------------------------------------------------
        # Componentes repetidos
        # -----------------------------------------------------

        component_ids = [
            str(item["component"].id)
            for item in components
        ]

        if (
            len(component_ids)
            != len(set(component_ids))
        ):
            raise serializers.ValidationError(
                {
                    "components": (
                        "No se puede registrar dos veces "
                        "el mismo componente."
                    )
                }
            )

        # -----------------------------------------------------
        # Los componentes deben pertenecer al material
        # -----------------------------------------------------

        for item in components:
            component = item["component"]

            if (
                component.material_id
                != material.id
            ):
                raise serializers.ValidationError(
                    {
                        "components": (
                            "Todos los componentes deben "
                            "pertenecer al material principal."
                        )
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        personnel_input = validated_data[
            "personnel"
        ]

        material_input = validated_data[
            "material"
        ]

        component_data = validated_data.pop(
            "components",
            [],
        )

        # -----------------------------------------------------
        # Bloqueamos Personnel durante la operación.
        # -----------------------------------------------------

        personnel = (
            Personnel.objects
            .select_for_update()
            .get(
                pk=personnel_input.pk
            )
        )

        # -----------------------------------------------------
        # Bloqueamos el material.
        #
        # Evita que dos solicitudes simultáneas
        # asignen el mismo material.
        # -----------------------------------------------------

        material = (
            SerializedMaterial.objects
            .select_for_update()
            .select_related(
                "unit",
                "armory",
                "specification",
                "specification__material_type",
            )
            .get(
                pk=material_input.pk
            )
        )

        # -----------------------------------------------------
        # Revalidamos después del bloqueo.
        # -----------------------------------------------------

        if not personnel.is_active:
            raise serializers.ValidationError(
                {
                    "personnel": (
                        "El personal se encuentra inactivo."
                    )
                }
            )

        if not material.is_active:
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material se encuentra inactivo."
                    )
                }
            )

        if (
            material.status
            != SerializedStatus.AVAILABLE
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material ya no se encuentra "
                        "DISPONIBLE."
                    )
                }
            )

        if (
            personnel.unit_id
            != material.unit_id
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material y el personal "
                        "deben pertenecer a la misma unidad."
                    )
                }
            )

        if IndividualAssignment.objects.filter(
            material=material,
            status=AssignmentStatus.ACTIVE,
        ).exists():
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material ya posee una "
                        "dotación activa."
                    )
                }
            )

        # -----------------------------------------------------
        # Crear dotación
        # -----------------------------------------------------

        assignment = IndividualAssignment(
            personnel=personnel,
            material=material,
            assigned_by=request.user,
            assignment_document=validated_data.get(
                "assignment_document",
                "",
            ),
            assignment_observations=validated_data.get(
                "assignment_observations",
                "",
            ),
            status=AssignmentStatus.ACTIVE,
        )

        try:
            assignment.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        assignment.save()

        # -----------------------------------------------------
        # Componentes entregados
        # -----------------------------------------------------

        for item in component_data:
            component_input = item[
                "component"
            ]

            component = (
                SerializedMaterialComponent.objects
                .select_for_update()
                .select_related(
                    "material",
                    "component_type",
                )
                .get(
                    pk=component_input.pk
                )
            )

            assignment_component = (
                IndividualAssignmentComponent(
                    assignment=assignment,
                    component=component,
                    quantity_delivered=item.get(
                        "quantity_delivered",
                        1,
                    ),
                    observations=item.get(
                        "observations",
                        "",
                    ),
                )
            )

            try:
                assignment_component.full_clean()
            except DjangoValidationError as exc:
                raise_drf_validation_error(exc)

            assignment_component.save()

        # -----------------------------------------------------
        # Inventario:
        # AVAILABLE -> ASSIGNED
        # -----------------------------------------------------

        material.status = (
            SerializedStatus.ASSIGNED
        )

        material.updated_by = (
            request.user
        )

        try:
            material.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        material.save()

        return assignment

    def to_representation(self, instance):
        return IndividualAssignmentSerializer(
            instance,
            context=self.context,
        ).data


# ============================================================
# DEVOLUCIÓN DE DOTACIÓN
# ============================================================


class IndividualAssignmentReturnSerializer(
    serializers.Serializer
):
    return_document = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        default="",
    )

    return_observations = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        request = self.context["request"]

        # -----------------------------------------------------
        # Bloquear dotación.
        # -----------------------------------------------------

        assignment = (
            IndividualAssignment.objects
            .select_for_update()
            .select_related(
                "personnel",
                "material",
            )
            .get(
                pk=instance.pk
            )
        )

        if (
            assignment.status
            != AssignmentStatus.ACTIVE
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        "Esta dotación ya fue devuelta."
                    )
                }
            )

        # -----------------------------------------------------
        # Bloquear material.
        # -----------------------------------------------------

        material = (
            SerializedMaterial.objects
            .select_for_update()
            .get(
                pk=assignment.material_id
            )
        )

        # -----------------------------------------------------
        # Cerrar dotación.
        # -----------------------------------------------------

        assignment.status = (
            AssignmentStatus.RETURNED
        )

        assignment.returned_at = (
            timezone.now()
        )

        assignment.return_document = (
            validated_data.get(
                "return_document",
                "",
            )
        )

        assignment.return_observations = (
            validated_data.get(
                "return_observations",
                "",
            )
        )

        assignment.returned_by = (
            request.user
        )

        try:
            assignment.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        assignment.save()

        # -----------------------------------------------------
        # Inventario:
        # ASSIGNED -> AVAILABLE
        # -----------------------------------------------------

        material.status = (
            SerializedStatus.AVAILABLE
        )

        material.updated_by = (
            request.user
        )

        try:
            material.full_clean()
        except DjangoValidationError as exc:
            raise_drf_validation_error(exc)

        material.save()

        return assignment

    def create(self, validated_data):
        raise NotImplementedError(
            "Este serializer solamente se utiliza "
            "para devolver una dotación existente."
        )

    def to_representation(self, instance):
        return IndividualAssignmentSerializer(
            instance,
            context=self.context,
        ).data