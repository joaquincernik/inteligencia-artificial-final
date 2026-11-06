"""Generación de reportes PDF a partir del Markdown de los reportes de Capazeta.

Reutiliza los formatters Markdown de ``report.py`` para que el PDF tenga el
mismo contenido que el ``.md`` y lo renderiza con ReportLab.
"""
import os
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from capazeta.tools.report import _sanitize, scan_to_markdown

_DEJAVU_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_fonts_ready = False

_INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_INLINE_ITALIC = re.compile(r"(?<![A-Za-z0-9])_([^_\n]+)_(?![A-Za-z0-9])")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


def _register_fonts() -> None:
    """Registra DejaVu (para acentos/símbolos) con fallback a Helvetica."""
    global _FONT, _FONT_BOLD, _fonts_ready
    if _fonts_ready:
        return
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", _DEJAVU_REGULAR))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", _DEJAVU_BOLD))
        registerFontFamily(
            "DejaVuSans",
            normal="DejaVuSans",
            bold="DejaVuSans-Bold",
            italic="DejaVuSans",
            boldItalic="DejaVuSans-Bold",
        )
        _FONT = "DejaVuSans"
        _FONT_BOLD = "DejaVuSans-Bold"
    except Exception:
        _FONT = "Helvetica"
        _FONT_BOLD = "Helvetica-Bold"
    _fonts_ready = True


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "CapazetaBody",
        parent=base["BodyText"],
        fontName=_FONT,
        fontSize=9,
        leading=12,
        spaceAfter=4,
    )
    return {
        "h1": ParagraphStyle(
            "CapazetaH1",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=17,
            leading=21,
            spaceBefore=2,
            spaceAfter=8,
            textColor=colors.HexColor("#1f3a5f"),
        ),
        "h2": ParagraphStyle(
            "CapazetaH2",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=12.5,
            leading=16,
            spaceBefore=8,
            spaceAfter=5,
            textColor=colors.HexColor("#1f3a5f"),
        ),
        "h3": ParagraphStyle(
            "CapazetaH3",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=10.5,
            leading=13,
            spaceBefore=6,
            spaceAfter=3,
            textColor=colors.HexColor("#33475b"),
        ),
        "body": body,
        "bullet": ParagraphStyle(
            "CapazetaBullet",
            parent=body,
            leftIndent=13,
            bulletIndent=2,
            spaceAfter=2,
        ),
        "quote": ParagraphStyle(
            "CapazetaQuote",
            parent=body,
            leftIndent=12,
            textColor=colors.HexColor("#4a5568"),
        ),
        "table_header": ParagraphStyle(
            "CapazetaTH",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=7.6,
            leading=9.5,
            textColor=colors.white,
            spaceAfter=0,
        ),
        "table_cell": ParagraphStyle(
            "CapazetaTD",
            parent=body,
            fontSize=7.6,
            leading=9.5,
            spaceAfter=0,
        ),
    }


def _inline(text: str) -> str:
    """Convierte el Markdown inline a marcado que entiende ``Paragraph``."""
    text = escape(text or "")
    text = _INLINE_CODE.sub(r'<font face="Courier">\1</font>', text)
    text = _INLINE_LINK.sub(
        lambda m: (
            f'<link href="{m.group(2)}"><font color="#1155cc">{m.group(1)}</font></link>'
        ),
        text,
    )
    text = _INLINE_BOLD.sub(r"<b>\1</b>", text)
    text = _INLINE_ITALIC.sub(r"<i>\1</i>", text)
    return text


def _is_table_line(line: str) -> bool:
    return line.strip().startswith("|")


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_RE.match(cell) for cell in cells)


def _make_table(rows: list[list[str]], styles: dict, available_width: float) -> Table:
    ncols = max(len(row) for row in rows)
    padded = [row + [""] * (ncols - len(row)) for row in rows]
    header, body = padded[0], padded[1:]

    data = [[Paragraph(_inline(cell), styles["table_header"]) for cell in header]]
    data += [
        [Paragraph(_inline(cell), styles["table_cell"]) for cell in row] for row in body
    ]

    col_width = available_width / ncols
    table = Table(data, colWidths=[col_width] * ncols, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b7c3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#eef2f7")],
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _markdown_to_flowables(
    content: str, styles: dict, available_width: float
) -> list:
    """Convierte el subconjunto de Markdown que generamos en flowables."""
    flowables = []
    lines = content.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        if _is_table_line(line):
            rows = []
            while index < len(lines) and _is_table_line(lines[index]):
                cells = _split_row(lines[index])
                if not _is_separator(cells):
                    rows.append(cells)
                index += 1
            if rows:
                flowables.append(Spacer(1, 4))
                flowables.append(_make_table(rows, styles, available_width))
                flowables.append(Spacer(1, 8))
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            flowables.append(Paragraph(_inline(heading.group(2)), styles[f"h{level}"]))
            index += 1
            continue

        if line.startswith(">"):
            flowables.append(
                Paragraph(_inline(line.lstrip(">").strip()), styles["quote"])
            )
            index += 1
            continue

        if line.startswith("- ") or line.startswith("* "):
            flowables.append(
                Paragraph(
                    _inline(line[2:].strip()),
                    styles["bullet"],
                    bulletText="\u2022",
                )
            )
            index += 1
            continue

        flowables.append(Paragraph(_inline(line), styles["body"]))
        index += 1

    return flowables


def _draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(_FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(
        1.5 * cm,
        1.0 * cm,
        f"Capazeta · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    canvas.drawRightString(A4[0] - 1.5 * cm, 1.0 * cm, f"Página {doc.page}")
    canvas.restoreState()


def markdown_to_pdf(content: str, output_path: str, title: str | None = None) -> str:
    """Renderiza ``content`` (Markdown) a un PDF en ``output_path``."""
    _register_fonts()
    styles = _build_styles()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    document = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.7 * cm,
        title=title or "Reporte Capazeta",
        author="Capazeta",
    )

    available_width = A4[0] - document.leftMargin - document.rightMargin
    flowables = _markdown_to_flowables(content, styles, available_width)
    if not flowables:
        flowables = [Paragraph("Sin contenido.", styles["body"])]

    document.build(flowables, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return output_path


def save_general_pdf_report(
    content: str, prefix: str, reports_dir: str = "reports"
) -> str:
    """Escribe un reporte PDF general en reports/ y devuelve la ruta generada."""
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(reports_dir, f"{_sanitize(prefix)}_{timestamp}.pdf")
    return markdown_to_pdf(content, path, title=prefix.replace("_", " ").title())


def save_pdf_report(data: dict, reports_dir: str = "reports") -> str:
    """Escribe el reporte PDF de un escaneo Nmap y devuelve la ruta generada."""
    os.makedirs(reports_dir, exist_ok=True)
    target = _sanitize(data.get("target", "scan"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(reports_dir, f"nmap_{target}_{timestamp}.pdf")
    return markdown_to_pdf(
        scan_to_markdown(data), path, title=f"Escaneo Nmap {target}"
    )
