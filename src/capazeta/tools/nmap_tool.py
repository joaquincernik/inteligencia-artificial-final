"""Herramienta de escaneo de red con Nmap para el subagente de infraestructura_redes."""
import json
import re
import shlex
from typing import Optional

from langchain_core.tools import tool

from capazeta.tools.pdf_report import save_pdf_report
from capazeta.tools.report import save_markdown_report
from capazeta.ui import progress

try:
    import nmap
except ImportError:  # pragma: no cover
    nmap = None

_HOST_RE = re.compile(r"^[A-Za-z0-9._:/\-]+$")

# Solo se permiten flags de Nmap sin valores y de bajo riesgo. Quedan fuera
# --script, -iL/-iR (lectura de hosts), -oN/-oG/-oX/-oA (escritura de archivos),
# -p (los puertos se controlan con el parámetro `ports`), -D/-S/-e (spoofing) y
# cualquier opción que reciba un valor arbitrario. Tampoco se incluyen -sS ni -O
# porque requieren privilegios de root y la tool corre sin sudo.
_ALLOWED_ARGUMENTS = {
    "-sT",
    "-sV",
    "-sn",
    "-Pn",
    "-F",
    "-n",
    "-R",
    "-v",
    "-vv",
    "--open",
    "--reason",
    "-6",
    "-T2",
    "-T3",
    "-T4",
    "--version-light",
    "--version-all",
}

_MAX_ARGUMENT_TOKENS = 8

_PORT_RE = re.compile(r"^(\d{1,5})(?:-(\d{1,5}))?$")


def _validate_target(target: str) -> Optional[str]:
    value = (target or "").strip()
    if not value:
        return "El target no puede estar vacío."
    # Un target que empieza con "-" podría interpretarse como un flag de Nmap.
    if value.startswith("-") or not _HOST_RE.match(value):
        return f"Target inválido: {target!r}"
    return None


def _validate_ports(ports: str) -> Optional[str]:
    value = (ports or "").strip()
    if not value:
        return "El rango de puertos no puede estar vacío."

    for raw_token in value.split(","):
        token = raw_token.strip()
        match = _PORT_RE.match(token)
        if not match:
            return (
                f"Puertos inválidos: {ports!r}. "
                "Usá el formato '22,80,443' o '1-1024'."
            )
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if not (1 <= start <= 65535 and 1 <= end <= 65535):
            return f"Puerto fuera de rango: {token!r}. Rango válido: 1-65535."
        if start > end:
            return f"Rango de puertos inválido: {token!r}."
    return None


def _validate_arguments(arguments: str) -> Optional[str]:
    try:
        tokens = shlex.split(arguments or "")
    except ValueError as exc:
        return f"Argumentos inválidos: {exc}"

    if len(tokens) > _MAX_ARGUMENT_TOKENS:
        return (
            f"Demasiados argumentos de Nmap (máximo {_MAX_ARGUMENT_TOKENS})."
        )

    invalid = [token for token in tokens if token not in _ALLOWED_ARGUMENTS]
    if invalid:
        allowed = ", ".join(sorted(_ALLOWED_ARGUMENTS))
        return (
            f"Argumentos no permitidos: {', '.join(invalid)}. "
            f"Opciones permitidas: {allowed}."
        )
    return None


def _scan_error(scanner) -> Optional[str]:
    """Extrae el error que Nmap reporta en el XML (python-nmap no lo lanza)."""
    info = scanner.scaninfo() or {}
    error = info.get("error")
    if not error:
        return None
    if isinstance(error, (list, tuple)):
        error = error[0]
    return str(error).strip() or "error desconocido de Nmap"


@tool
def run_nmap_scan(
    target: str,
    ports: str = "1-1024",
    arguments: str = "-sV",
    save_md: bool = False,
    save_pdf: bool = False,
) -> str:
    """Escanea un host o rango de red con Nmap y devuelve puertos y servicios.

    Usar únicamente sobre infraestructura propia o con autorización explícita.
    El target, los puertos y cada opción de Nmap se validan antes de ejecutar:
    solo se aceptan flags de la lista blanca (sin scripts, archivos de salida ni
    listas de hosts).

    Args:
        target: IP, hostname o rango CIDR (ej. "192.168.1.10", "10.0.0.0/24").
        ports: Puertos a escanear (ej. "22,80,443" o "1-1024"). Solo números y
            rangos separados por comas. Se ignora con -sn y -F, que definen su
            propio conjunto de puertos.
        arguments: Opciones de Nmap permitidas (ej. "-sV", "-sT -T4"). Se valida
            contra una lista blanca; no se permiten scripts ni redirección de
            salida.
        save_md: Si es True, además guarda un reporte Markdown en reports/.
        save_pdf: Si es True, además guarda un reporte PDF en reports/.
    """
    if nmap is None:
        return json.dumps({"error": "python-nmap no está instalado."}, ensure_ascii=False)

    error = _validate_target(target)
    if error:
        return json.dumps({"error": error}, ensure_ascii=False)

    arguments = (arguments or "").strip() or "-sV"
    error = _validate_arguments(arguments)
    if error:
        return json.dumps({"error": error}, ensure_ascii=False)

    tokens = shlex.split(arguments)

    if "-sn" in tokens and "-F" in tokens:
        return json.dumps(
            {
                "error": "No se pueden combinar -sn (descubrir hosts) y -F "
                "(top 100 de puertos). Elegí uno de los dos."
            },
            ensure_ascii=False,
        )

    if "-6" in tokens and ":" not in target:
        return json.dumps(
            {"error": "El flag -6 requiere un target IPv6 (con ':')."},
            ensure_ascii=False,
        )

    # -sn hace descubrimiento de hosts y -F usa su propia lista de puertos:
    # en ambos casos python-nmap no debe agregar el -p implícito.
    skip_explicit_ports = "-sn" in tokens or "-F" in tokens
    if skip_explicit_ports:
        scan_ports = None
    else:
        error = _validate_ports(ports)
        if error:
            return json.dumps({"error": error}, ensure_ascii=False)
        scan_ports = ",".join(token.strip() for token in ports.split(","))

    progress("Ejecutando Nmap...")

    scanner = nmap.PortScanner()
    try:
        scanner.scan(hosts=target.strip(), ports=scan_ports, arguments=arguments)
    except nmap.PortScannerError as exc:
        return json.dumps({"error": f"Nmap error: {exc}"}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"Error inesperado: {exc}"}, ensure_ascii=False)

    error = _scan_error(scanner)
    if error:
        return json.dumps({"error": f"Nmap: {error}"}, ensure_ascii=False)

    results = []
    for host in scanner.all_hosts():
        host_info = {
            "host": host,
            "state": scanner[host].state(),
            "addresses": scanner[host].get("addresses", {}),
            "hostnames": scanner[host].get("hostnames", []),
            "ports": [],
        }
        for proto in scanner[host].all_protocols():
            for port in sorted(scanner[host][proto].keys()):
                entry = scanner[host][proto][port]
                host_info["ports"].append(
                    {
                        "protocol": proto,
                        "port": port,
                        "state": entry.get("state"),
                        "service": entry.get("name"),
                        "product": entry.get("product"),
                        "version": entry.get("version"),
                    }
                )
        results.append(host_info)

    data = {"target": target, "arguments": arguments, "results": results}
    if not results:
        data["note"] = (
            "Nmap no encontró hosts activos. Si la red bloquea ICMP, "
            "repetí el escaneo con '-Pn'."
        )
    if save_md:
        data["file"] = save_markdown_report(data)
    if save_pdf:
        data["pdf_file"] = save_pdf_report(data)
    return json.dumps(data, ensure_ascii=False)
