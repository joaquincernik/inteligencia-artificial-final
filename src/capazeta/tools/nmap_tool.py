"""Herramienta de escaneo de red con Nmap para el subagente de infraestructura_redes."""
import json
import re
from typing import Optional

from langchain_core.tools import tool

from capazeta.tools.report import save_markdown_report

try:
    import nmap
except ImportError:  # pragma: no cover
    nmap = None

_HOST_RE = re.compile(r"^[A-Za-z0-9._:/\-]+$")


def _validate_target(target: str) -> Optional[str]:
    if not target or not target.strip():
        return "El target no puede estar vacío."
    if not _HOST_RE.match(target.strip()):
        return f"Target inválido: {target!r}"
    return None


@tool
def run_nmap_scan(
    target: str,
    ports: str = "1-1024",
    arguments: str = "-sV",
    save_md: bool = False,
) -> str:
    """Escanea un host o rango de red con Nmap y devuelve puertos y servicios.

    Usar únicamente sobre infraestructura propia o con autorización explícita.

    Args:
        target: IP, hostname o rango CIDR (ej. "192.168.1.10", "10.0.0.0/24").
        ports: Puertos a escanear (ej. "22,80,443" o "1-1024").
        arguments: Argumentos de Nmap (ej. "-sV", "-sS -O").
        save_md: Si es True, además guarda un reporte Markdown en reports/.
    """
    if nmap is None:
        return json.dumps({"error": "python-nmap no está instalado."}, ensure_ascii=False)

    error = _validate_target(target)
    if error:
        return json.dumps({"error": error}, ensure_ascii=False)

    print("realizando nmap...", flush=True)

    scanner = nmap.PortScanner()
    try:
        scanner.scan(hosts=target.strip(), ports=ports, arguments=arguments)
    except nmap.PortScannerError as exc:
        return json.dumps({"error": f"Nmap error: {exc}"}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"Error inesperado: {exc}"}, ensure_ascii=False)

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

    data = {"target": target, "results": results}
    if save_md:
        data["file"] = save_markdown_report(data)
    return json.dumps(data, ensure_ascii=False)
