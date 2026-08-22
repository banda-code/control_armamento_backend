from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.personnel.models import Personnel
from apps.reports.models import IndividualFiliationConfig

from apps.audit.utils import log_event

from .services import (
    build_armament_detail,
    build_general_material_report,
    build_individual_filiation_report,
    export_armament_detail_pdf,
    export_armament_detail_xlsx,
    export_general_material_pdf,
    export_general_material_xlsx,
    export_individual_filiation_pdf,
    get_armament_options,
    resolve_report_unit,
)


# ============================================================
# UTILIDADES
# ============================================================


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(
            exc.message_dict,
            status=status.HTTP_400_BAD_REQUEST,
        )

    messages = getattr(exc, "messages", None)

    return Response(
        {
            "detail": (
                messages[0]
                if messages
                else str(exc)
            )
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _generated_by(user):
    full_name = getattr(user, "full_name", "")
    return full_name or getattr(user, "email", "") or str(user)


# ============================================================
# OPCIONES PARA EL SELECTOR DE ARMAMENTO
# ============================================================


class ArmamentReportOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        return Response(
            {
                "unit": {
                    "id": str(unit.id),
                    "name": unit.name,
                },
                "results": get_armament_options(unit),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# VISTA PREVIA: ARMAMENTO ESPECÍFICO
# ============================================================


class ArmamentDetailPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        specification_id = request.query_params.get("specification")

        if not specification_id:
            return Response(
                {"detail": "Debe seleccionar un armamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )

            report = build_armament_detail(
                unit,
                specification_id,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        return Response(report, status=status.HTTP_200_OK)


# ============================================================
# VISTA PREVIA: REPORTE GENERAL
# ============================================================


class GeneralMaterialPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )

            report = build_general_material_report(unit)
        except DjangoValidationError as exc:
            return _validation_response(exc)

        return Response(report, status=status.HTTP_200_OK)


# ============================================================
# DESCARGA: ARMAMENTO ESPECÍFICO
# ============================================================


class ArmamentDetailExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        specification_id = request.query_params.get("specification")
        export_format = request.query_params.get("file_format", "pdf").lower()

        if not specification_id:
            return Response(
                {"detail": "Debe seleccionar un armamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if export_format not in {"pdf", "xlsx"}:
            return Response(
                {"detail": "Formato no válido. Use pdf o xlsx."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )

            report = build_armament_detail(
                unit,
                specification_id,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        generated_by = _generated_by(request.user)

        if export_format == "xlsx":
            stream = export_armament_detail_xlsx(
                report,
                generated_by,
            )
            content_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
            extension = "xlsx"
        else:
            stream = export_armament_detail_pdf(
                report,
                generated_by,
            )
            content_type = "application/pdf"
            extension = "pdf"

        safe_name = (
            report["weapon"]["material_type"]
            .replace(" ", "_")
            .replace("/", "-")
        )

        filename = f"armamento_{safe_name}.{extension}"

        log_event(
            request=request,
            action="ARMAMENT_REPORT_EXPORTED",
            actor=request.user,
            target=unit,
            unit=unit,
            metadata={
                "report": "ARMAMENT_DETAIL",
                "format": export_format,
                "specification_id": specification_id,
                "total": report["total"],
            },
        )

        return FileResponse(
            stream,
            as_attachment=True,
            filename=filename,
            content_type=content_type,
        )


# ============================================================
# DESCARGA: REPORTE GENERAL
# ============================================================


class GeneralMaterialExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        export_format = request.query_params.get("file_format", "pdf").lower()

        if export_format not in {"pdf", "xlsx"}:
            return Response(
                {"detail": "Formato no válido. Use pdf o xlsx."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )

            report = build_general_material_report(unit)
        except DjangoValidationError as exc:
            return _validation_response(exc)

        generated_by = _generated_by(request.user)

        if export_format == "xlsx":
            stream = export_general_material_xlsx(
                report,
                generated_by,
            )
            content_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
            extension = "xlsx"
        else:
            stream = export_general_material_pdf(
                report,
                generated_by,
            )
            content_type = "application/pdf"
            extension = "pdf"

        filename = f"parte_general_material_belico.{extension}"

        log_event(
            request=request,
            action="GENERAL_MATERIAL_REPORT_EXPORTED",
            actor=request.user,
            target=unit,
            unit=unit,
            metadata={
                "report": "GENERAL_MATERIAL",
                "format": export_format,
                "sections": report["total_sections"],
            },
        )

        return FileResponse(
            stream,
            as_attachment=True,
            filename=filename,
            content_type=content_type,
        )


# ============================================================
# DESCARGA: FILIACIÓN DE ARMAMENTO DE DOTACIÓN INDIVIDUAL
# ============================================================


class IndividualFiliationExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        personnel_id = request.query_params.get("personnel")

        if not personnel_id:
            return Response(
                {
                    "detail": (
                        "Debe seleccionar el personal "
                        "para generar la filiación."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requested_unit_id = request.query_params.get(
                "unit"
            )

            # --------------------------------------------------------
            # USUARIO CON ALCANCE GLOBAL
            #
            # Si no seleccionó una unidad manualmente,
            # utilizamos automáticamente la unidad del personal.
            # --------------------------------------------------------

            if (
                getattr(
                    request.user,
                    "has_global_scope",
                    False,
                )
                and not requested_unit_id
            ):
                personnel_unit_id = (
                    Personnel.objects
                    .filter(
                        pk=personnel_id,
                        is_active=True,
                    )
                    .values_list(
                        "unit_id",
                        flat=True,
                    )
                    .first()
                )

                if not personnel_unit_id:
                    raise DjangoValidationError(
                        "El personal seleccionado no existe "
                        "o no tiene una unidad asignada."
                    )

                requested_unit_id = (
                    personnel_unit_id
                )

            # --------------------------------------------------------
            # RESOLVER UNIDAD SEGÚN LOS PERMISOS DEL USUARIO
            # --------------------------------------------------------

            unit = resolve_report_unit(
                request.user,
                requested_unit_id,
            )

            # --------------------------------------------------------
            # CONSTRUIR FILIACIÓN
            # --------------------------------------------------------

            report = build_individual_filiation_report(
                unit,
                personnel_id,
            )

        except DjangoValidationError as exc:
            return _validation_response(exc)

        generated_by = _generated_by(request.user)

        stream = export_individual_filiation_pdf(
            report,
            generated_by,
        )

        full_name = (
            report.get("personnel", {})
            .get("full_name", "personal")
        )

        safe_name = (
            full_name.strip()
            .replace(" ", "_")
            .replace("/", "-")
            .replace("\\", "-")
        )

        filename = (
            f"filiacion_armamento_{safe_name}.pdf"
        )

        log_event(
            request=request,
            action="INDIVIDUAL_FILIATION_EXPORTED",
            actor=request.user,
            target=unit,
            unit=unit,
            metadata={
                "report": "INDIVIDUAL_FILIATION",
                "personnel_id": personnel_id,
                "personnel_name": full_name,
                "total_assignments": report.get(
                    "total_assignments",
                    0,
                ),
            },
        )

        return FileResponse(
            stream,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )
# ============================================================
# CONFIGURACIÓN DE FIRMANTES - FILIACIÓN INDIVIDUAL
# ============================================================


class IndividualFiliationConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def _person_data(self, person):
        if not person:
            return None

        return {
            "id": str(person.id),
            "tin": person.tin,
            "full_name": person.full_name,
            "rank": (
                person.rank.abbreviation
                if person.rank
                else ""
            ),
            "position": (
                person.position.name
                if person.position
                else ""
            ),
        }

    def get(self, request):
        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        config = (
            IndividualFiliationConfig.objects
            .filter(unit=unit)
            .select_related(
                "verification_responsible__rank",
                "verification_responsible__position",
                "logistics_chief__rank",
                "logistics_chief__position",
                "unit_commander__rank",
                "unit_commander__position",
            )
            .first()
        )

        return Response(
            {
                "unit": {
                    "id": str(unit.id),
                    "name": unit.name,
                },
                "config": {
                    "id": (
                        str(config.id)
                        if config
                        else None
                    ),
                    "verification_responsible": (
                        self._person_data(
                            config.verification_responsible
                        )
                        if config
                        else None
                    ),
                    "logistics_chief": (
                        self._person_data(
                            config.logistics_chief
                        )
                        if config
                        else None
                    ),
                    "unit_commander": (
                        self._person_data(
                            config.unit_commander
                        )
                        if config
                        else None
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        try:
            unit = resolve_report_unit(
                request.user,
                request.query_params.get("unit"),
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        def get_person(field_name):
            person_id = request.data.get(
                field_name
            )

            if not person_id:
                return None

            person = (
                Personnel.objects
                .filter(
                    pk=person_id,
                    unit=unit,
                    is_active=True,
                )
                .select_related(
                    "rank",
                    "position",
                )
                .first()
            )

            if not person:
                raise DjangoValidationError(
                    {
                        field_name: (
                            "El personal seleccionado "
                            "no existe o no pertenece "
                            "a la unidad."
                        )
                    }
                )

            return person

        try:
            verification_responsible = get_person(
                "verification_responsible"
            )

            logistics_chief = get_person(
                "logistics_chief"
            )

            unit_commander = get_person(
                "unit_commander"
            )

            config, _ = (
                IndividualFiliationConfig.objects
                .get_or_create(
                    unit=unit
                )
            )

            config.verification_responsible = (
                verification_responsible
            )

            config.logistics_chief = (
                logistics_chief
            )

            config.unit_commander = (
                unit_commander
            )

            config.full_clean()
            config.save()

        except DjangoValidationError as exc:
            return _validation_response(exc)

        log_event(
            request=request,
            action="INDIVIDUAL_FILIATION_CONFIG_UPDATED",
            actor=request.user,
            target=unit,
            unit=unit,
            metadata={
                "verification_responsible": (
                    str(
                        verification_responsible.id
                    )
                    if verification_responsible
                    else None
                ),
                "logistics_chief": (
                    str(logistics_chief.id)
                    if logistics_chief
                    else None
                ),
                "unit_commander": (
                    str(unit_commander.id)
                    if unit_commander
                    else None
                ),
            },
        )

        return Response(
            {
                "detail": (
                    "Configuración de firmantes "
                    "actualizada correctamente."
                ),
                "config": {
                    "id": str(config.id),
                    "verification_responsible": (
                        self._person_data(
                            verification_responsible
                        )
                    ),
                    "logistics_chief": (
                        self._person_data(
                            logistics_chief
                        )
                    ),
                    "unit_commander": (
                        self._person_data(
                            unit_commander
                        )
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )