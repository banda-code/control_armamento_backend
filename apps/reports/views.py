from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_event

from .services import (
    build_armament_detail,
    build_general_material_report,
    export_armament_detail_pdf,
    export_armament_detail_xlsx,
    export_general_material_pdf,
    export_general_material_xlsx,
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
