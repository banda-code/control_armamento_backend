from collections import defaultdict
from io import BytesIO

from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.utils import timezone

from apps.accounts.scopes import get_user_unit_id
from apps.inventory.models import (
    ControlMethod,
    MaterialSpecification,
    SerializedMaterial,
    StockBatch,
)
from apps.organization.models import Unit


CATEGORY_ORDER = {
    "ARMAMENTO": 10,
    "ARMA BLANCA": 20,
    "CLASE V": 30,
    "MUNICION": 30,
    "MUNICIÓN": 30,
    "AGENTES QUIMICOS": 40,
    "AGENTES QUÍMICOS": 40,
    "EXPLOSIVOS": 50,
}


# ============================================================
# ÁMBITO DE UNIDAD
# ============================================================


def resolve_report_unit(user, requested_unit_id=None):
    """
    Devuelve la unidad sobre la que puede emitirse el reporte.

    - Usuario con alcance global: puede indicar ?unit=<uuid>.
    - Usuario sin alcance global: siempre queda limitado a su unidad.
    """

    if getattr(user, "has_global_scope", False):
        unit_id = requested_unit_id or getattr(user, "unit_id", None)

        if not unit_id:
            raise ValidationError(
                "Debe seleccionar una unidad para generar el reporte."
            )

        try:
            return Unit.objects.get(pk=unit_id)
        except Unit.DoesNotExist as exc:
            raise ValidationError("La unidad seleccionada no existe.") from exc

    unit_id = get_user_unit_id(user)

    if not unit_id:
        raise ValidationError(
            "El usuario no tiene una unidad asignada para generar reportes."
        )

    try:
        return Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist as exc:
        raise ValidationError("La unidad del usuario no existe.") from exc


# ============================================================
# OPCIONES DE ARMAMENTO / MATERIAL SERIALIZADO
# ============================================================


def get_armament_options(unit):
    rows = (
        SerializedMaterial.objects
        .filter(
            unit=unit,
            is_active=True,
            specification__is_active=True,
            specification__material_type__is_active=True,
            specification__material_type__control_method=(
                ControlMethod.SERIALIZED
            ),
        )
        .values(
            "specification_id",
            "specification__material_type__category__name",
            "specification__material_type__name",
            "specification__name",
            "specification__manufacturer__name",
            "specification__country__name",
            "specification__caliber__name",
        )
        .annotate(total=Count("id"))
        .order_by(
            "specification__material_type__category__name",
            "specification__material_type__name",
            "specification__name",
        )
    )

    return [
        {
            "id": str(row["specification_id"]),
            "category": (
                row["specification__material_type__category__name"] or ""
            ),
            "material_type": row["specification__material_type__name"] or "",
            "specification": row["specification__name"] or "",
            "manufacturer": row["specification__manufacturer__name"] or "",
            "country": row["specification__country__name"] or "",
            "caliber": row["specification__caliber__name"] or "",
            "total": row["total"],
            "label": " - ".join(
                value
                for value in [
                    row["specification__material_type__name"],
                    row["specification__name"],
                    row["specification__caliber__name"],
                ]
                if value
            ),
        }
        for row in rows
    ]


# ============================================================
# REPORTE POR TIPO / ESPECIFICACIÓN DE ARMAMENTO
# ============================================================


def build_armament_detail(unit, specification_id):
    try:
        specification = (
            MaterialSpecification.objects
            .select_related(
                "material_type",
                "material_type__category",
                "manufacturer",
                "country",
                "caliber",
            )
            .get(pk=specification_id)
        )
    except MaterialSpecification.DoesNotExist as exc:
        raise ValidationError("El armamento seleccionado no existe.") from exc

    materials = list(
        SerializedMaterial.objects
        .filter(
            unit=unit,
            specification=specification,
            is_active=True,
        )
        .select_related(
            "unit",
            "armory",
            "specification",
            "specification__material_type",
            "specification__manufacturer",
            "specification__country",
            "specification__caliber",
        )
        .prefetch_related(
            "components__component_type",
        )
        .order_by(
            "institutional_code",
            "identification_number",
        )
    )

    status_summary = defaultdict(int)
    condition_summary = defaultdict(int)
    rows = []

    for index, material in enumerate(materials, start=1):
        status_summary[material.get_status_display()] += 1
        condition_summary[material.get_physical_condition_display()] += 1

        components = []
        for component in material.components.all():
            if not component.is_active:
                continue

            description = component.component_type.name

            if component.identification_number:
                description += f" ({component.identification_number})"

            if component.quantity > 1:
                description += f" x{component.quantity}"

            components.append(description)

        rows.append(
            {
                "nro": index,
                "institutional_code": material.institutional_code,
                "identification_number": material.identification_number,
                "status": material.status,
                "status_display": material.get_status_display(),
                "physical_condition": material.physical_condition,
                "physical_condition_display": (
                    material.get_physical_condition_display()
                ),
                "armory": material.armory.name,
                "manufacturing_year": material.manufacturing_year or "",
                "acquisition_source": material.acquisition_source or "",
                "registration_document": (
                    material.registration_document or ""
                ),
                "components": ", ".join(components),
                "observations": material.observations or "",
            }
        )

    return {
        "report_type": "ARMAMENT_DETAIL",
        "generated_at": timezone.localtime(),
        "unit": {
            "id": str(unit.id),
            "name": unit.name,
        },
        "weapon": {
            "id": str(specification.id),
            "category": specification.material_type.category.name,
            "material_type": specification.material_type.name,
            "specification": specification.name,
            "manufacturer": (
                specification.manufacturer.name
                if specification.manufacturer
                else ""
            ),
            "country": (
                specification.country.name
                if specification.country
                else ""
            ),
            "caliber": (
                specification.caliber.name
                if specification.caliber
                else ""
            ),
            "description": specification.description or "",
        },
        "total": len(rows),
        "status_summary": dict(status_summary),
        "condition_summary": dict(condition_summary),
        "rows": rows,
    }


# ============================================================
# REPORTE GENERAL DE MATERIAL BÉLICO
# ============================================================


def build_general_material_report(unit):
    grouped = defaultdict(list)

    serialized_rows = (
        SerializedMaterial.objects
        .filter(
            unit=unit,
            is_active=True,
            specification__is_active=True,
        )
        .values(
            "specification_id",
            "specification__material_type__category__name",
            "specification__material_type__name",
            "specification__name",
            "specification__caliber__name",
        )
        .annotate(total=Count("id"))
        .order_by(
            "specification__material_type__category__name",
            "specification__material_type__name",
            "specification__name",
        )
    )

    for row in serialized_rows:
        category = (
            row["specification__material_type__category__name"]
            or "SIN CATEGORÍA"
        )

        description = " ".join(
            value
            for value in [
                row["specification__material_type__name"],
                row["specification__name"],
                row["specification__caliber__name"],
            ]
            if value
        )

        grouped[category].append(
            {
                "source": "SERIALIZED",
                "specification_id": str(row["specification_id"]),
                "description": description,
                "unit_of_measure": "UND.",
                "total": row["total"],
            }
        )

    quantity_rows = (
        StockBatch.objects
        .filter(
            unit=unit,
            is_active=True,
            stock_material__is_active=True,
            stock_material__specification__is_active=True,
        )
        .values(
            "stock_material__specification_id",
            "stock_material__specification__material_type__category__name",
            "stock_material__specification__material_type__name",
            "stock_material__specification__name",
            "stock_material__specification__caliber__name",
            "stock_material__unit_of_measure__symbol",
            "stock_material__unit_of_measure__name",
        )
        .annotate(total=Sum("current_quantity"))
        .order_by(
            "stock_material__specification__material_type__category__name",
            "stock_material__specification__material_type__name",
            "stock_material__specification__name",
        )
    )

    for row in quantity_rows:
        category = (
            row[
                "stock_material__specification__material_type__category__name"
            ]
            or "SIN CATEGORÍA"
        )

        description = " ".join(
            value
            for value in [
                row["stock_material__specification__material_type__name"],
                row["stock_material__specification__name"],
                row["stock_material__specification__caliber__name"],
            ]
            if value
        )

        grouped[category].append(
            {
                "source": "QUANTITY",
                "specification_id": str(
                    row["stock_material__specification_id"]
                ),
                "description": description,
                "unit_of_measure": (
                    row["stock_material__unit_of_measure__symbol"]
                    or row["stock_material__unit_of_measure__name"]
                    or "UND."
                ),
                "total": float(row["total"] or 0),
            }
        )

    sections = []

    for category, rows in grouped.items():
        subtotal_by_unit = defaultdict(float)

        for row in rows:
            subtotal_by_unit[row["unit_of_measure"]] += float(row["total"])

        sections.append(
            {
                "category": category,
                "rows": sorted(
                    rows,
                    key=lambda item: item["description"],
                ),
                "subtotal_by_unit": dict(subtotal_by_unit),
            }
        )

    sections.sort(
        key=lambda section: (
            CATEGORY_ORDER.get(section["category"].upper(), 999),
            section["category"],
        )
    )

    return {
        "report_type": "GENERAL_MATERIAL",
        "generated_at": timezone.localtime(),
        "unit": {
            "id": str(unit.id),
            "name": unit.name,
        },
        "sections": sections,
        "total_sections": len(sections),
    }


# ============================================================
# EXCEL
# ============================================================


def _excel_styles():
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    navy = "0F172A"
    slate = "334155"
    light = "E2E8F0"
    white = "FFFFFF"

    thin = Side(style="thin", color="94A3B8")

    return {
        "navy": navy,
        "slate": slate,
        "light": light,
        "white": white,
        "title_font": Font(name="Arial", bold=True, size=14, color=navy),
        "subtitle_font": Font(name="Arial", bold=True, size=11, color=navy),
        "normal_font": Font(name="Arial", size=9, color="111827"),
        "header_font": Font(name="Arial", bold=True, size=9, color=white),
        "section_font": Font(name="Arial", bold=True, size=10, color=white),
        "navy_fill": PatternFill("solid", fgColor=navy),
        "slate_fill": PatternFill("solid", fgColor=slate),
        "light_fill": PatternFill("solid", fgColor=light),
        "border": Border(left=thin, right=thin, top=thin, bottom=thin),
        "center": Alignment(horizontal="center", vertical="center", wrap_text=True),
        "left": Alignment(horizontal="left", vertical="center", wrap_text=True),
    }


def export_armament_detail_xlsx(report, generated_by=""):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    styles = _excel_styles()
    wb = Workbook()
    ws = wb.active
    ws.title = "Armamento"

    ws.merge_cells("A1:K1")
    ws["A1"] = "ARMADA BOLIVIANA"
    ws["A1"].font = styles["title_font"]
    ws["A1"].alignment = styles["center"]

    ws.merge_cells("A2:K2")
    ws["A2"] = report["unit"]["name"]
    ws["A2"].font = styles["subtitle_font"]
    ws["A2"].alignment = styles["center"]

    ws.merge_cells("A4:K4")
    ws["A4"] = "INVENTARIO DE MATERIAL BÉLICO - DETALLE POR ARMAMENTO"
    ws["A4"].font = styles["subtitle_font"]
    ws["A4"].alignment = styles["center"]

    weapon = report["weapon"]

    metadata = [
        ("TIPO DE ARMAMENTO", weapon["material_type"]),
        ("MODELO / ESPECIFICACIÓN", weapon["specification"]),
        ("FABRICANTE", weapon["manufacturer"] or "S/D"),
        ("INDUSTRIA / PAÍS", weapon["country"] or "S/D"),
        ("CALIBRE", weapon["caliber"] or "S/D"),
        ("TOTAL EN LA UNIDAD", report["total"]),
    ]

    row = 6
    for label, value in metadata:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=1).font = styles["header_font"]
        ws.cell(row=row, column=1).fill = styles["slate_fill"]
        ws.cell(row=row, column=1).alignment = styles["left"]

        ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=11)
        ws.cell(row=row, column=4, value=value)
        ws.cell(row=row, column=4).font = styles["normal_font"]
        ws.cell(row=row, column=4).alignment = styles["left"]
        row += 1

    row += 1

    headers = [
        "N°",
        "CÓDIGO",
        "N° SERIE / IDENTIFICACIÓN",
        "ESTADO",
        "CONDICIÓN",
        "PAÑOL",
        "AÑO FAB.",
        "PROCEDENCIA / ADQUISICIÓN",
        "DOCUMENTO DE ALTA",
        "ACCESORIOS / COMPONENTES",
        "OBSERVACIONES",
    ]

    header_row = row

    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = styles["header_font"]
        cell.fill = styles["navy_fill"]
        cell.alignment = styles["center"]
        cell.border = styles["border"]

    for item in report["rows"]:
        row += 1
        values = [
            item["nro"],
            item["institutional_code"],
            item["identification_number"],
            item["status_display"],
            item["physical_condition_display"],
            item["armory"],
            item["manufacturing_year"],
            item["acquisition_source"],
            item["registration_document"],
            item["components"],
            item["observations"],
        ]

        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.font = styles["normal_font"]
            cell.alignment = styles["center"] if col in {1, 4, 5, 7} else styles["left"]
            cell.border = styles["border"]

    row += 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    ws.cell(row=row, column=1, value=f"TOTAL: {report['total']} REGISTROS")
    ws.cell(row=row, column=1).font = styles["subtitle_font"]

    row += 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=11)
    ws.cell(
        row=row,
        column=1,
        value=(
            f"Generado por: {generated_by or '—'} | "
            f"Fecha: {report['generated_at'].strftime('%d/%m/%Y %H:%M')}"
        ),
    )
    ws.cell(row=row, column=1).font = styles["normal_font"]
    ws.cell(row=row, column=1).alignment = styles["left"]

    widths = [6, 16, 22, 16, 16, 22, 12, 26, 24, 30, 34]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:K{max(header_row, row - 4)}"
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"1:{header_row}"

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_general_material_xlsx(report, generated_by=""):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    styles = _excel_styles()
    wb = Workbook()
    ws = wb.active
    ws.title = "Parte General"

    ws.merge_cells("A1:D1")
    ws["A1"] = "ARMADA BOLIVIANA"
    ws["A1"].font = styles["title_font"]
    ws["A1"].alignment = styles["center"]

    ws.merge_cells("A2:D2")
    ws["A2"] = report["unit"]["name"]
    ws["A2"].font = styles["subtitle_font"]
    ws["A2"].alignment = styles["center"]

    ws.merge_cells("A4:D4")
    ws["A4"] = "PARTE GENERAL DE MATERIAL BÉLICO Y EXISTENCIAS"
    ws["A4"].font = styles["subtitle_font"]
    ws["A4"].alignment = styles["center"]

    row = 6

    for index, section in enumerate(report["sections"], start=1):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        ws.cell(
            row=row,
            column=1,
            value=f"{index}.- {section['category']}",
        )
        ws.cell(row=row, column=1).font = styles["section_font"]
        ws.cell(row=row, column=1).fill = styles["slate_fill"]
        ws.cell(row=row, column=1).alignment = styles["left"]
        row += 1

        headers = ["N°", "TIPO / ESPECIFICACIÓN", "UNIDAD MEDIDA", "TOTAL"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = styles["header_font"]
            cell.fill = styles["navy_fill"]
            cell.alignment = styles["center"]
            cell.border = styles["border"]

        for item_index, item in enumerate(section["rows"], start=1):
            row += 1
            values = [
                item_index,
                item["description"],
                item["unit_of_measure"],
                item["total"],
            ]

            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.font = styles["normal_font"]
                cell.alignment = styles["center"] if col in {1, 3, 4} else styles["left"]
                cell.border = styles["border"]

        for unit_symbol, subtotal in section["subtotal_by_unit"].items():
            row += 1
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
            ws.cell(row=row, column=1, value=f"SUBTOTAL {unit_symbol}")
            ws.cell(row=row, column=1).font = styles["subtitle_font"]
            ws.cell(row=row, column=1).fill = styles["light_fill"]
            ws.cell(row=row, column=3, value=unit_symbol)
            ws.cell(row=row, column=4, value=subtotal)

            for col in range(1, 5):
                ws.cell(row=row, column=col).border = styles["border"]
                ws.cell(row=row, column=col).alignment = styles["center"]

        row += 2

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    ws.cell(
        row=row,
        column=1,
        value=(
            f"Generado por: {generated_by or '—'} | "
            f"Fecha: {report['generated_at'].strftime('%d/%m/%Y %H:%M')}"
        ),
    )
    ws.cell(row=row, column=1).font = styles["normal_font"]

    widths = [7, 80, 18, 18]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# ============================================================
# PDF
# ============================================================


def _pdf_base_styles():
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#334155"),
            spaceAfter=3,
        ),
        "normal": ParagraphStyle(
            "ReportNormal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
        ),
    }


def export_armament_detail_pdf(report, generated_by=""):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = _pdf_base_styles()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title="Reporte de Armamento - FORTALEZA",
        author="Sistema FORTALEZA",
    )

    story = []
    story.append(Paragraph("ARMADA BOLIVIANA", styles["title"]))
    story.append(Paragraph(report["unit"]["name"], styles["subtitle"]))
    story.append(
        Paragraph(
            "INVENTARIO DE MATERIAL BÉLICO - DETALLE POR ARMAMENTO",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 3 * mm))

    weapon = report["weapon"]

    meta_data = [
        ["TIPO", weapon["material_type"], "MODELO", weapon["specification"]],
        ["FABRICANTE", weapon["manufacturer"] or "S/D", "PAÍS", weapon["country"] or "S/D"],
        ["CALIBRE", weapon["caliber"] or "S/D", "TOTAL", str(report["total"])],
    ]

    meta_table = Table(
        meta_data,
        colWidths=[28 * mm, 66 * mm, 28 * mm, 66 * mm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94A3B8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    headers = [
        "N°",
        "CÓDIGO",
        "SERIE / IDENT.",
        "ESTADO",
        "CONDICIÓN",
        "PAÑOL",
        "AÑO",
        "PROCEDENCIA",
        "DOCUMENTO",
        "ACCESORIOS",
        "OBSERVACIONES",
    ]

    table_data = [headers]

    for item in report["rows"]:
        table_data.append(
            [
                str(item["nro"]),
                item["institutional_code"],
                item["identification_number"],
                item["status_display"],
                item["physical_condition_display"],
                item["armory"],
                str(item["manufacturing_year"] or ""),
                Paragraph(item["acquisition_source"] or "", styles["small"]),
                Paragraph(item["registration_document"] or "", styles["small"]),
                Paragraph(item["components"] or "", styles["small"]),
                Paragraph(item["observations"] or "", styles["small"]),
            ]
        )

    detail_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            7 * mm,
            19 * mm,
            25 * mm,
            19 * mm,
            19 * mm,
            24 * mm,
            11 * mm,
            29 * mm,
            28 * mm,
            35 * mm,
            43 * mm,
        ],
    )

    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 6.5),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 6.2),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94A3B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )

    story.append(detail_table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            (
                f"Total registrado: {report['total']} | "
                f"Generado por: {generated_by or '—'} | "
                f"Fecha: {report['generated_at'].strftime('%d/%m/%Y %H:%M')}"
            ),
            styles["normal"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer


def export_general_material_pdf(report, generated_by=""):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = _pdf_base_styles()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Parte General de Material Bélico - FORTALEZA",
        author="Sistema FORTALEZA",
    )

    story = []
    story.append(Paragraph("ARMADA BOLIVIANA", styles["title"]))
    story.append(Paragraph(report["unit"]["name"], styles["subtitle"]))
    story.append(
        Paragraph(
            "PARTE GENERAL DE MATERIAL BÉLICO Y EXISTENCIAS",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    for index, section in enumerate(report["sections"], start=1):
        section_header = Table(
            [[f"{index}.- {section['category']}"]],
            colWidths=[180 * mm],
        )
        section_header.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(section_header)

        table_data = [["N°", "TIPO / ESPECIFICACIÓN", "U.M.", "TOTAL"]]

        for item_index, item in enumerate(section["rows"], start=1):
            table_data.append(
                [
                    str(item_index),
                    Paragraph(item["description"], styles["normal"]),
                    item["unit_of_measure"],
                    str(item["total"]),
                ]
            )

        for symbol, subtotal in section["subtotal_by_unit"].items():
            table_data.append(
                [
                    "",
                    Paragraph(f"<b>SUBTOTAL {symbol}</b>", styles["normal"]),
                    symbol,
                    str(subtotal),
                ]
            )

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[12 * mm, 128 * mm, 20 * mm, 20 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94A3B8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            (
                f"Generado por: {generated_by or '—'} | "
                f"Fecha: {report['generated_at'].strftime('%d/%m/%Y %H:%M')}"
            ),
            styles["normal"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer
