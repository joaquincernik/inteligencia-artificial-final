"""Configuración de pytest: opciones CLI y fixtures. Acá no hay tests.

Los tests de Nmap viven en ``test_nmap.py`` y los de PDFs en ``test_pdf.py``.
Este archivo solo existe porque pytest exige declarar las opciones de línea de
comandos (``--nmap-target``, ``--nmap-arguments``, ``--nmap-ports``) en un
``conftest.py`` o en un plugin.
"""
import os

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("capazeta", "escaneo real de Nmap (opt-in)")
    group.addoption(
        "--nmap-target",
        action="store",
        default=os.environ.get("CAPAZETA_NMAP_TARGET"),
        metavar="RED",
        help=(
            "IP, CIDR o hostname a escanear en el test de integración. "
            "Sin este flag el test se omite. También se puede definir con "
            "la variable CAPAZETA_NMAP_TARGET."
        ),
    )
    group.addoption(
        "--nmap-arguments",
        action="store",
        default="-sn",
        metavar="ARGS",
        help=(
            "Flags de Nmap para el test real (default: -sn). "
            "Se validan contra la allowlist de la tool."
        ),
    )
    group.addoption(
        "--nmap-ports",
        action="store",
        default="1-1024",
        metavar="PUERTOS",
        help=(
            "Puertos para el test real (default: 1-1024). "
            "Se ignoran con -sn y -F, que definen su propio conjunto."
        ),
    )


@pytest.fixture
def nmap_target(request):
    target = (request.config.getoption("nmap_target") or "").strip()
    if not target:
        pytest.skip(
            "Test de red omitido: pasá --nmap-target 192.168.0.0/24 "
            "(o definí CAPAZETA_NMAP_TARGET)."
        )
    return target


@pytest.fixture
def nmap_arguments(request):
    return (request.config.getoption("nmap_arguments") or "-sn").strip()


@pytest.fixture
def nmap_ports(request):
    return (request.config.getoption("nmap_ports") or "1-1024").strip()
