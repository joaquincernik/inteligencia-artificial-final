"""Tests de generación de reportes PDF con ReportLab.

Escriben siempre en ``tmp_path``, así que no tocan ``reports/`` ni necesitan
red. Cubren PDFs válidos, tablas/enlaces/código, sanitización de nombres y
contenido vacío o con caracteres especiales.
"""
from pathlib import Path

import pytest

from capazeta.tools.pdf_report import (
    markdown_to_pdf,
    save_general_pdf_report,
    save_pdf_report,
)


def assert_pdf(path: Path) -> None:
    """Comprueba que el archivo es un PDF no vacío y cerrado correctamente."""
    assert path.exists(), f"No se generó el PDF: {path}"
    data = path.read_bytes()
    assert data.startswith(b"%PDF-"), "Falta la firma %PDF-"
    assert data.rstrip().endswith(b"%%EOF"), "El PDF no termina en %%EOF"
    assert len(data) > 500, "El PDF es sospechosamente chico"


def test_markdown_a_pdf_genera_pdf_valido(tmp_path):
    contenido = (
        "# Reporte de prueba\n\n"
        "Texto con **negrita**, _énfasis_ y `codigo`.\n\n"
        "- primer ítem\n"
        "- segundo ítem\n"
    )
    salida = tmp_path / "reporte.pdf"

    resultado = markdown_to_pdf(contenido, str(salida), title="Demo")

    assert resultado == str(salida)
    assert_pdf(salida)


def test_pdf_con_tabla_enlaces_y_codigo(tmp_path):
    contenido = (
        "# Tabla\n\n"
        "| ID | Técnica |\n"
        "| --- | --- |\n"
        "| T1046 | [Network Service Discovery](https://attack.mitre.org/techniques/T1046/) |\n\n"
        "> Cita con _énfasis_ y **negrita**.\n"
    )
    salida = tmp_path / "tabla.pdf"

    markdown_to_pdf(contenido, str(salida))

    assert_pdf(salida)


def test_save_pdf_report_sanitiza_target(tmp_path):
    data = {"target": "../../etc/passwd", "results": []}
    reports_dir = tmp_path / "reports"

    ruta = Path(save_pdf_report(data, reports_dir=str(reports_dir)))

    assert ruta.parent == reports_dir
    assert ruta.name.startswith("nmap_etc_passwd_")
    assert ruta.suffix == ".pdf"
    assert "/" not in ruta.name and ".." not in ruta.name
    assert_pdf(ruta)


def test_save_general_pdf_report_usa_prefix(tmp_path):
    reports_dir = tmp_path / "reports"

    ruta = Path(
        save_general_pdf_report(
            "# Informe\n\nContenido del reporte.",
            "informe wazuh",
            reports_dir=str(reports_dir),
        )
    )

    assert ruta.parent == reports_dir
    assert ruta.name.startswith("informe_wazuh_")
    assert_pdf(ruta)


@pytest.mark.parametrize(
    "contenido",
    ["", "<script>alert(1)</script>\n\nA & B < C"],
)
def test_pdf_con_contenido_vacio_o_html(tmp_path, contenido):
    salida = tmp_path / "edge.pdf"

    markdown_to_pdf(contenido, str(salida))

    assert_pdf(salida)
