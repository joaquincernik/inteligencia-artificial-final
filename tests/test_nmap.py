"""Tests de Nmap: 10 rápidos (sin red) + 1 de integración opt-in.

Los rápidos validan la allowlist y la construcción del JSON con un
``PortScanner`` falso, así que corren sin red, credenciales ni el binario de
Nmap. El último ejecuta Nmap de verdad y solo corre si se pasa
``--nmap-target``.
"""
import json
import shutil

import pytest

from capazeta.tools import nmap_tool
from capazeta.tools.nmap_tool import (
    _validate_arguments,
    _validate_ports,
    _validate_target,
    run_nmap_scan,
)


@pytest.fixture
def sin_escaneo(monkeypatch):
    """Rompe si algo intenta instanciar el PortScanner real."""

    def _bomba(*args, **kwargs):
        raise AssertionError("No se debe ejecutar un escaneo real en los tests")

    monkeypatch.setattr(nmap_tool.nmap, "PortScanner", _bomba)


# ---------------------------------------------------------------------------
# Validación y allowlist (sin red)
# ---------------------------------------------------------------------------

def test_argumentos_permitidos():
    assert _validate_arguments("-sV") is None
    assert _validate_arguments("-sT -T4 --open") is None
    assert _validate_arguments("-sn -Pn -v") is None


@pytest.mark.parametrize(
    "arguments",
    [
        "--script vuln",
        "--script=vuln",
        "--script http-shellshock",
    ],
)
def test_rechaza_script_nmap(arguments):
    error = _validate_arguments(arguments)
    assert error is not None
    assert "no permitidos" in error


@pytest.mark.parametrize(
    "arguments",
    [
        "-sV; rm -rf /",
        "-sV && whoami",
        "$(whoami)",
        "`id`",
        "| cat /etc/passwd",
    ],
)
def test_rechaza_inyeccion_de_shell(arguments):
    assert _validate_arguments(arguments) is not None


@pytest.mark.parametrize(
    "arguments",
    [
        "-p 22",
        "-oN salida.txt",
        "-oX salida.xml",
        "-iL hosts.txt",
        "-D 1.2.3.4",
        "-S 1.2.3.4",
        "-e eth0",
        "--script-args foo=bar",
        "-O",
        "-sS",
    ],
)
def test_rechaza_flags_peligrosos(arguments):
    assert _validate_arguments(arguments) is not None


def test_rechaza_demasiados_argumentos():
    error = _validate_arguments(" ".join(["-sV"] * 9))
    assert error is not None
    assert "Demasiados" in error


def test_rechaza_comillas_sin_cerrar():
    error = _validate_arguments('-sV "sin cerrar')
    assert error is not None
    assert "Argumentos inválidos" in error


@pytest.mark.parametrize(
    "target, valido",
    [
        ("192.168.1.10", True),
        ("10.0.0.0/24", True),
        ("example.com", True),
        ("::1", True),
        ("host-01.local", True),
        ("", False),
        ("   ", False),
        ("-sV", False),
        ("8.8.8.8; rm -rf /", False),
        ("host name", False),
        ("8.8.8.8 && whoami", False),
    ],
)
def test_valida_target(target, valido):
    error = _validate_target(target)
    assert (error is None) is valido


@pytest.mark.parametrize(
    "ports, valido",
    [
        ("22,80,443", True),
        ("1-1024", True),
        ("65535", True),
        (" 22 , 80 ", True),
        ("", False),
        ("0", False),
        ("65536", False),
        ("100-50", False),
        ("22;rm", False),
        ("22 80", False),
    ],
)
def test_valida_puertos(ports, valido):
    error = _validate_ports(ports)
    assert (error is None) is valido


# ---------------------------------------------------------------------------
# Tool con PortScanner falso (sin red)
# ---------------------------------------------------------------------------

def test_tool_rechaza_script_sin_ejecutar_nmap(sin_escaneo):
    resultado = json.loads(
        run_nmap_scan.invoke({"target": "127.0.0.1", "arguments": "--script vuln"})
    )
    assert "error" in resultado
    assert "--script" in resultado["error"]


class _FakeHost(dict):
    def state(self):
        return "up"

    def all_protocols(self):
        return []


class _FakePortScanner:
    """Imita lo mínimo de python-nmap que usa la tool."""

    instancias = []

    def __init__(self):
        self.scan_kwargs = None
        self._hosts = {}
        _FakePortScanner.instancias.append(self)

    def scan(self, **kwargs):
        self.scan_kwargs = kwargs
        self._hosts = {"192.168.0.26": _FakeHost()}

    def scaninfo(self):
        return {}

    def all_hosts(self):
        return list(self._hosts)

    def __getitem__(self, host):
        return self._hosts[host]


def test_tool_escaneo_valido_con_scanner_falso(monkeypatch):
    monkeypatch.setattr(nmap_tool.nmap, "PortScanner", _FakePortScanner)

    resultado = json.loads(
        run_nmap_scan.invoke(
            {
                "target": "192.168.0.26",
                "ports": "22,80,443",
                "arguments": "-sV -T4",
            }
        )
    )

    assert "error" not in resultado
    assert resultado["target"] == "192.168.0.26"
    assert resultado["results"][0]["host"] == "192.168.0.26"

    scanner = _FakePortScanner.instancias[-1]
    assert scanner.scan_kwargs == {
        "hosts": "192.168.0.26",
        "ports": "22,80,443",
        "arguments": "-sV -T4",
    }


# ---------------------------------------------------------------------------
# Test de integración contra una red real (opt-in, marker `network`)
# ---------------------------------------------------------------------------

@pytest.mark.network
def test_escaneo_real_de_red(nmap_target, nmap_arguments, nmap_ports):
    if shutil.which("nmap") is None:
        pytest.skip("El binario nmap no está instalado.")

    error = _validate_target(nmap_target)
    assert error is None, f"--nmap-target inválido: {error}"

    resultado = json.loads(
        run_nmap_scan.invoke(
            {
                "target": nmap_target,
                "ports": nmap_ports,
                "arguments": nmap_arguments,
            }
        )
    )

    assert "error" not in resultado, f"Nmap devolvió un error: {resultado['error']}"

    hosts = resultado.get("results") or []
    print(
        f"\nNmap {nmap_target} con '{nmap_arguments}': "
        f"{len(hosts)} host(s) encontrados"
    )
    for host in hosts[:20]:
        print(f"  - {host.get('host')} ({host.get('state')})")

    assert hosts, (
        f"Nmap no encontró hosts activos en {nmap_target}. "
        'Si la red bloquea ICMP, probá --nmap-arguments "-sT -F --open".'
    )
