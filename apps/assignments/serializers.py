from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from apps.accounts.scopes import get_user_unit_id
from apps.inventory.models import (
    AllocationType,
    SerializedMaterial,
    SerializedMaterialComponent,
    SerializedStatus,
)
from apps.personnel.models import Personnel

from .models import (
    AssignmentCustodyState,
    AssignmentPhotoMoment,
    AssignmentStatus,
    IndividualAssignment,
    IndividualAssignmentComponent,
    IndividualAssignmentCustodyItem,
    IndividualAssignmentCustodyMovement,
    IndividualAssignmentPhoto,
)
from .services import create_custody_movement


# ============================================================
# UTILIDAD DE VALIDACIÓN
# ============================================================


def raise_drf_validation_error(exc):
    """
    Convierte ValidationError de Django en
    ValidationError de Django REST Framework.
    """

    if hasattr(
        exc,
        "message_dict",
    ):
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
        queryset=(
            SerializedMaterialComponent.objects
            .filter(
                is_active=True
            )
            .select_related(
                "material",
                "component_type",
            )
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
# CUSTODIA - ITEM
# ============================================================


class IndividualAssignmentCustodyItemSerializer(
    serializers.ModelSerializer
):
    material = serializers.UUIDField(
        source="assignment.material_id",
        read_only=True,
    )

    material_code = serializers.CharField(
        source=(
            "assignment.material.institutional_code"
        ),
        read_only=True,
    )

    material_identification_number = (
        serializers.CharField(
            source=(
                "assignment.material."
                "identification_number"
            ),
            read_only=True,
        )
    )

    material_specification = serializers.CharField(
        source=(
            "assignment.material."
            "specification.name"
        ),
        read_only=True,
    )

    class Meta:
        model = (
            IndividualAssignmentCustodyItem
        )

        fields = [
            "id",
            "assignment",
            "material",
            "material_code",
            "material_identification_number",
            "material_specification",
            "created_at",
        ]

        read_only_fields = fields


# ============================================================
# CUSTODIA - CONSULTA DE MOVIMIENTO
# ============================================================


class IndividualAssignmentCustodyMovementSerializer(
    serializers.ModelSerializer
):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )

    personnel_tin = serializers.CharField(
        source="personnel.tin",
        read_only=True,
    )

    personnel_name = serializers.CharField(
        source="personnel.full_name",
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

    items = (
        IndividualAssignmentCustodyItemSerializer(
            many=True,
            read_only=True,
        )
    )

    total_items = serializers.SerializerMethodField()

    class Meta:
        model = (
            IndividualAssignmentCustodyMovement
        )

        fields = [
            "id",

            "movement_type",
            "movement_type_display",
            "movement_at",

            "personnel",
            "personnel_tin",
            "personnel_name",

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

    def get_total_items(
        self,
        obj,
    ):
        return len(
            obj.items.all()
        )


# ============================================================
# CUSTODIA - ENTREGA / RECEPCIÓN
# ============================================================


class IndividualAssignmentCustodyActionSerializer(
    serializers.Serializer
):
    assignments = serializers.PrimaryKeyRelatedField(
        queryset=(
            IndividualAssignment.objects
            .select_related(
                "personnel",
                "material",
                "material__unit",
                "material__armory",
            )
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

    def validate_assignments(
        self,
        assignments,
    ):
        if not assignments:
            raise serializers.ValidationError(
                (
                    "Debe seleccionar al menos "
                    "una dotación."
                )
            )

        ids = [
            str(
                item.id
            )
            for item in assignments
        ]

        if (
            len(ids)
            != len(
                set(ids)
            )
        ):
            raise serializers.ValidationError(
                (
                    "No puede seleccionar dos veces "
                    "la misma dotación."
                )
            )

        return assignments

    def create(
        self,
        validated_data,
    ):
        request = self.context[
            "request"
        ]

        movement_type = self.context[
            "custody_movement_type"
        ]

        assignments = validated_data.pop(
            "assignments"
        )

        try:
            return create_custody_movement(
                actor=request.user,

                assignment_ids=[
                    item.id
                    for item in assignments
                ],

                movement_type=movement_type,

                reason=validated_data[
                    "reason"
                ],

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
            raise_drf_validation_error(
                exc
            )

    def to_representation(
        self,
        instance,
    ):
        return (
            IndividualAssignmentCustodyMovementSerializer(
                instance,
                context=self.context,
            ).data
        )


# ============================================================
# DOTACIÓN - CONSULTA
# ============================================================


class IndividualAssignmentSerializer(
    serializers.ModelSerializer
):
    # --------------------------------------------------------
    # Personal
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Material
    # --------------------------------------------------------

    material_code = serializers.CharField(
        source="material.institutional_code",
        read_only=True,
    )

    material_identification_number = (
        serializers.CharField(
            source=(
                "material.identification_number"
            ),
            read_only=True,
        )
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

    # --------------------------------------------------------
    # Estado administrativo
    # --------------------------------------------------------

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    # --------------------------------------------------------
    # Estado físico de custodia
    # --------------------------------------------------------

    custody_status = (
        serializers.SerializerMethodField()
    )

    custody_status_display = (
        serializers.SerializerMethodField()
    )

    # --------------------------------------------------------
    # Usuarios
    # --------------------------------------------------------

    assigned_by_email = serializers.CharField(
        source="assigned_by.email",
        read_only=True,
    )

    returned_by_email = serializers.CharField(
        source="returned_by.email",
        read_only=True,
        default=None,
    )

    # --------------------------------------------------------
    # Componentes
    # --------------------------------------------------------

    components = (
        IndividualAssignmentComponentSerializer(
            source="assigned_components",
            many=True,
            read_only=True,
        )
    )

    # --------------------------------------------------------
    # Fotografías
    # --------------------------------------------------------

    photos = serializers.SerializerMethodField()

    def get_photos(
        self,
        obj,
    ):
        photos = (
            obj.photos
            .select_related(
                "uploaded_by"
            )
            .all()
        )

        return (
            IndividualAssignmentPhotoSerializer(
                photos,
                many=True,
                context=self.context,
            ).data
        )

    # --------------------------------------------------------
    # Custodia
    # --------------------------------------------------------

    def get_custody_status(
        self,
        obj,
    ):
        return (
            obj.get_current_custody_state()
        )

    def get_custody_status_display(
        self,
        obj,
    ):
        value = (
            obj.get_current_custody_state()
        )

        return dict(
            AssignmentCustodyState.choices
        ).get(
            value,
            value,
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

            # Dotación
            "assigned_at",
            "assignment_document",
            "assignment_observations",
            "assigned_by",
            "assigned_by_email",

            # Estado
            "status",
            "status_display",

            # Custodia física
            "custody_status",
            "custody_status_display",

            # Cierre definitivo
            "returned_at",
            "return_document",
            "return_observations",
            "returned_by",
            "returned_by_email",

            # Detalle
            "components",
            "photos",

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
        queryset=(
            Personnel.objects
            .filter(
                is_active=True
            )
            .select_related(
                "unit"
            )
        )
    )

    material = serializers.PrimaryKeyRelatedField(
        queryset=(
            SerializedMaterial.objects
            .filter(
                is_active=True,
                allocation_type=(
                    AllocationType.INDIVIDUAL
                ),
            )
            .select_related(
                "unit",
                "armory",
                "specification",
                (
                    "specification"
                    "__material_type"
                ),
            )
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

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    def validate(
        self,
        attrs,
    ):
        personnel = attrs[
            "personnel"
        ]

        material = attrs[
            "material"
        ]

        components = attrs.get(
            "components",
            [],
        )

        request = self.context.get(
            "request"
        )

        # ----------------------------------------------------
        # MATERIAL INDIVIDUAL
        # ----------------------------------------------------

        if (
            material.allocation_type
            != AllocationType.INDIVIDUAL
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material seleccionado "
                        "no corresponde a dotación "
                        "individual."
                    )
                }
            )

        # ----------------------------------------------------
        # DISPONIBILIDAD
        # ----------------------------------------------------

        if (
            material.status
            != SerializedStatus.AVAILABLE
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material debe encontrarse "
                        "DISPONIBLE para iniciar una "
                        "dotación."
                    )
                }
            )

        # ----------------------------------------------------
        # NO PUEDE EXISTIR OTRA DOTACIÓN ACTIVA
        #
        # Una dotación RETURNED es historial y NO impide
        # una futura nueva dotación.
        # ----------------------------------------------------

        active_exists = (
            IndividualAssignment.objects
            .filter(
                material=material,
                status=AssignmentStatus.ACTIVE,
            )
            .exists()
        )

        if active_exists:
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material ya posee una "
                        "dotación activa."
                    )
                }
            )

        # ----------------------------------------------------
        # PERSONAL DEBE TENER UNIDAD
        # ----------------------------------------------------

        if not personnel.unit_id:
            raise serializers.ValidationError(
                {
                    "personnel": (
                        "El personal debe estar "
                        "asociado a una unidad."
                    )
                }
            )

        # ----------------------------------------------------
        # MISMA UNIDAD
        # ----------------------------------------------------

        if (
            personnel.unit_id
            != material.unit_id
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material y el personal "
                        "deben pertenecer a la "
                        "misma unidad."
                    )
                }
            )

        # ----------------------------------------------------
        # ALCANCE DEL USUARIO
        # ----------------------------------------------------

        if (
            request
            and request.user
            and request.user.is_authenticated
            and not request.user.has_global_scope
        ):
            user_unit_id = (
                get_user_unit_id(
                    request.user
                )
            )

            if not user_unit_id:
                raise serializers.ValidationError(
                    {
                        "personnel": (
                            "El usuario no tiene una "
                            "unidad institucional "
                            "asociada."
                        )
                    }
                )

            if (
                str(
                    user_unit_id
                )
                != str(
                    personnel.unit_id
                )
            ):
                raise serializers.ValidationError(
                    {
                        "personnel": (
                            "No puede registrar "
                            "dotaciones para otra "
                            "unidad."
                        )
                    }
                )

        # ----------------------------------------------------
        # COMPONENTES REPETIDOS
        # ----------------------------------------------------

        component_ids = [
            str(
                item[
                    "component"
                ].id
            )
            for item in components
        ]

        if (
            len(
                component_ids
            )
            != len(
                set(
                    component_ids
                )
            )
        ):
            raise serializers.ValidationError(
                {
                    "components": (
                        "No se puede registrar "
                        "dos veces el mismo "
                        "componente."
                    )
                }
            )

        # ----------------------------------------------------
        # COMPONENTES DEL MISMO MATERIAL
        # ----------------------------------------------------

        for item in components:
            component = item[
                "component"
            ]

            if (
                component.material_id
                != material.id
            ):
                raise serializers.ValidationError(
                    {
                        "components": (
                            "Todos los componentes "
                            "deben pertenecer al "
                            "material principal."
                        )
                    }
                )

        return attrs

    # ========================================================
    # CREAR
    # ========================================================

    @transaction.atomic
    def create(
        self,
        validated_data,
    ):
        request = self.context[
            "request"
        ]

        personnel_input = (
            validated_data[
                "personnel"
            ]
        )

        material_input = (
            validated_data[
                "material"
            ]
        )

        component_data = (
            validated_data.pop(
                "components",
                [],
            )
        )

        # ----------------------------------------------------
        # BLOQUEAR PERSONAL
        # ----------------------------------------------------

        personnel = (
            Personnel.objects
            .select_for_update()
            .get(
                pk=personnel_input.pk
            )
        )

        # ----------------------------------------------------
        # BLOQUEAR MATERIAL
        # ----------------------------------------------------

        material = (
            SerializedMaterial.objects
            .select_for_update()
            .select_related(
                "unit",
                "armory",
                "specification",
                (
                    "specification"
                    "__material_type"
                ),
            )
            .get(
                pk=material_input.pk
            )
        )

        # ----------------------------------------------------
        # REVALIDACIÓN DESPUÉS DEL BLOQUEO
        # ----------------------------------------------------

        if not personnel.is_active:
            raise serializers.ValidationError(
                {
                    "personnel": (
                        "El personal se "
                        "encuentra inactivo."
                    )
                }
            )

        if not material.is_active:
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material se "
                        "encuentra inactivo."
                    )
                }
            )

        if (
            material.allocation_type
            != AllocationType.INDIVIDUAL
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material no corresponde "
                        "a dotación individual."
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
                        "El material ya no se "
                        "encuentra DISPONIBLE."
                    )
                }
            )

        if not personnel.unit_id:
            raise serializers.ValidationError(
                {
                    "personnel": (
                        "El personal debe estar "
                        "asociado a una unidad."
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
                        "deben pertenecer a la "
                        "misma unidad."
                    )
                }
            )

        # ----------------------------------------------------
        # REVALIDAR QUE NO EXISTA DOTACIÓN ACTIVA
        # ----------------------------------------------------

        active_exists = (
            IndividualAssignment.objects
            .filter(
                material=material,
                status=AssignmentStatus.ACTIVE,
            )
            .exists()
        )

        if active_exists:
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material ya posee una "
                        "dotación activa."
                    )
                }
            )

        # ----------------------------------------------------
        # REVALIDAR ALCANCE
        # ----------------------------------------------------

        if not request.user.has_global_scope:
            user_unit_id = (
                get_user_unit_id(
                    request.user
                )
            )

            if not user_unit_id:
                raise serializers.ValidationError(
                    {
                        "personnel": (
                            "El usuario no tiene una "
                            "unidad institucional "
                            "asociada."
                        )
                    }
                )

            if (
                str(
                    user_unit_id
                )
                != str(
                    personnel.unit_id
                )
            ):
                raise serializers.ValidationError(
                    {
                        "personnel": (
                            "No puede registrar "
                            "dotaciones para otra "
                            "unidad."
                        )
                    }
                )

        # ----------------------------------------------------
        # CREAR DOTACIÓN
        #
        # Al crearse:
        # - Dotación = ACTIVE
        # - Material = ASSIGNED
        # - Custodia inicial = ARMORY
        #
        # La entrega física se registra aparte mediante:
        # custody-deliver/
        # ----------------------------------------------------

        assignment = IndividualAssignment(
            personnel=personnel,
            material=material,
            assigned_by=request.user,

            assignment_document=(
                validated_data.get(
                    "assignment_document",
                    "",
                )
            ),

            assignment_observations=(
                validated_data.get(
                    "assignment_observations",
                    "",
                )
            ),

            status=AssignmentStatus.ACTIVE,
        )

        try:
            assignment.full_clean()

        except DjangoValidationError as exc:
            raise_drf_validation_error(
                exc
            )

        assignment.save()

        # ----------------------------------------------------
        # COMPONENTES
        # ----------------------------------------------------

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

                    quantity_delivered=(
                        item.get(
                            "quantity_delivered",
                            1,
                        )
                    ),

                    observations=(
                        item.get(
                            "observations",
                            "",
                        )
                    ),
                )
            )

            try:
                assignment_component.full_clean()

            except DjangoValidationError as exc:
                raise_drf_validation_error(
                    exc
                )

            assignment_component.save()

        # ----------------------------------------------------
        # INVENTARIO
        # AVAILABLE -> ASSIGNED
        # ----------------------------------------------------

        material.status = (
            SerializedStatus.ASSIGNED
        )

        material.updated_by = (
            request.user
        )

        try:
            material.full_clean()

        except DjangoValidationError as exc:
            raise_drf_validation_error(
                exc
            )

        material.save()

        return assignment

    def to_representation(
        self,
        instance,
    ):
        return IndividualAssignmentSerializer(
            instance,
            context=self.context,
        ).data


# ============================================================
# CIERRE DEFINITIVO DE DOTACIÓN
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
        request = self.context[
            "request"
        ]

        # ----------------------------------------------------
        # BLOQUEAR DOTACIÓN
        # ----------------------------------------------------

        assignment = (
            IndividualAssignment.objects
            .select_for_update()
            .select_related(
                "personnel",
                "material",
                "material__unit",
                "material__armory",
            )
            .get(
                pk=instance.pk
            )
        )

        # ----------------------------------------------------
        # DEBE ESTAR ACTIVA
        # ----------------------------------------------------

        if (
            assignment.status
            != AssignmentStatus.ACTIVE
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        "Esta dotación ya se "
                        "encuentra finalizada."
                    )
                }
            )

        # ----------------------------------------------------
        # EL MATERIAL DEBE ESTAR FÍSICAMENTE EN EL PAÑOL
        #
        # Una simple recepción temporal NO cierra la dotación.
        # ----------------------------------------------------

        if (
            assignment.get_current_custody_state()
            != AssignmentCustodyState.ARMORY
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        "Antes de cerrar "
                        "definitivamente la dotación "
                        "debe registrar la recepción "
                        "física del material en el "
                        "pañol."
                    )
                }
            )

        # ----------------------------------------------------
        # BLOQUEAR MATERIAL
        # ----------------------------------------------------

        material = (
            SerializedMaterial.objects
            .select_for_update()
            .get(
                pk=assignment.material_id
            )
        )

        # ----------------------------------------------------
        # DEBE SEGUIR ADMINISTRATIVAMENTE ASIGNADO
        # ----------------------------------------------------

        if (
            material.status
            != SerializedStatus.ASSIGNED
        ):
            raise serializers.ValidationError(
                {
                    "material": (
                        "El material no se encuentra "
                        "en estado ASIGNADO y la "
                        "dotación no puede cerrarse."
                    )
                }
            )

        # ----------------------------------------------------
        # CERRAR DOTACIÓN
        # ----------------------------------------------------

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
            raise_drf_validation_error(
                exc
            )

        assignment.save()

        # ----------------------------------------------------
        # INVENTARIO
        #
        # Ahora sí:
        # ASSIGNED -> AVAILABLE
        #
        # porque la dotación administrativa terminó.
        # ----------------------------------------------------

        material.status = (
            SerializedStatus.AVAILABLE
        )

        material.updated_by = (
            request.user
        )

        try:
            material.full_clean()

        except DjangoValidationError as exc:
            raise_drf_validation_error(
                exc
            )

        material.save()

        return assignment

    def create(
        self,
        validated_data,
    ):
        raise NotImplementedError(
            (
                "Este serializer solamente se "
                "utiliza para cerrar una "
                "dotación existente."
            )
        )

    def to_representation(
        self,
        instance,
    ):
        return IndividualAssignmentSerializer(
            instance,
            context=self.context,
        ).data


# ============================================================
# FOTOGRAFÍAS
# ============================================================


class IndividualAssignmentPhotoSerializer(
    serializers.ModelSerializer
):
    moment_display = serializers.CharField(
        source="get_moment_display",
        read_only=True,
    )

    photo_type_display = serializers.CharField(
        source="get_photo_type_display",
        read_only=True,
    )

    uploaded_by_email = serializers.CharField(
        source="uploaded_by.email",
        read_only=True,
    )

    class Meta:
        model = IndividualAssignmentPhoto

        fields = [
            "id",
            "assignment",

            "moment",
            "moment_display",

            "photo_type",
            "photo_type_display",

            "photo",
            "description",

            "uploaded_by",
            "uploaded_by_email",

            "created_at",
        ]

        read_only_fields = [
            "id",
            "assignment",
            "uploaded_by",
            "uploaded_by_email",
            "moment_display",
            "photo_type_display",
            "created_at",
        ]

    def validate(
        self,
        attrs,
    ):
        assignment = self.context.get(
            "assignment"
        )

        moment = attrs.get(
            "moment"
        )

        if not assignment:
            raise serializers.ValidationError(
                {
                    "assignment": (
                        "No se pudo determinar "
                        "la dotación individual."
                    )
                }
            )

        # ----------------------------------------------------
        # RETURN = CIERRE DEFINITIVO
        #
        # No confundir con RECEIPT de custodia.
        # ----------------------------------------------------

        if (
            moment
            == AssignmentPhotoMoment.RETURN
            and assignment.status
            != AssignmentStatus.RETURNED
        ):
            raise serializers.ValidationError(
                {
                    "moment": (
                        "Las fotografías de "
                        "devolución definitiva solo "
                        "pueden registrarse después "
                        "del cierre de la dotación."
                    )
                }
            )

        return attrs

    def create(
        self,
        validated_data,
    ):
        request = self.context[
            "request"
        ]

        assignment = self.context[
            "assignment"
        ]

        return (
            IndividualAssignmentPhoto.objects.create(
                assignment=assignment,
                uploaded_by=request.user,
                **validated_data,
            )
        )