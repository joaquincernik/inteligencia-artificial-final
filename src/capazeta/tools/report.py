"""Formateo y guardado de reportes en Markdown (Nmap, Wazuh, MITRE ATT&CK)."""
import os
import re
from datetime import datetime


def scan_to_markdown(data: dict) -> str:
    """Convierte el resultado de un escaneo Nmap a un reporte Markdown."""
    target = data.get("target", "desconocido")
    results = data.get("results", []) or []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Reporte de escaneo Nmap",
        "",
        f"- **Target:** `{target}`",
        f"- **Fecha:** {now}",
        f"- **Hosts encontrados:** {len(results)}",
        "",
    ]

    if not results:
        lines.append("_No se encontraron hosts._")
        return "\n".join(lines) + "\n"

    for host_info in results:
        addresses = host_info.get("addresses") or {}
        hostnames = host_info.get("hostnames") or []
        names = ", ".join(h.get("name", "") for h in hostnames if h.get("name")) or "-"
        addr = ", ".join(f"{k}={v}" for k, v in addresses.items()) or host_info.get("host", "-")

        lines += [
            f"## Host `{host_info.get('host', '-')}`",
            "",
            f"- **Estado:** {host_info.get('state', '-')}",
            f"- **Direcciones:** {addr}",
            f"- **Hostnames:** {names}",
            "",
        ]

        ports = host_info.get("ports") or []
        if not ports:
            lines += ["_Sin puertos abiertos._", ""]
            continue

        lines += [
            "| Puerto | Protocolo | Estado | Servicio | Producto | Versión |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for p in ports:
            lines.append(
                "| {port} | {proto} | {state} | {svc} | {prod} | {ver} |".format(
                    port=p.get("port", ""),
                    proto=p.get("protocol", ""),
                    state=p.get("state", ""),
                    svc=p.get("service", "") or "",
                    prod=p.get("product", "") or "",
                    ver=p.get("version", "") or "",
                )
            )
        lines.append("")

    return "\n".join(lines)


def wazuh_alerts_to_markdown(data: dict) -> str:
    """Convierte resultados de búsqueda de alertas de Wazuh a Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = data.get("total", 0)
    alerts = data.get("alerts", []) or []

    lines = [
        "# Reporte de Alertas de Wazuh",
        "",
        f"- **Fecha:** {now}",
        f"- **Total de alertas:** {total}",
        "",
    ]

    if not alerts:
        lines.append("_No se encontraron alertas._")
        return "\n".join(lines) + "\n"

    lines += [
        "| Timestamp | Agente | Nivel | Regla | Descripción | MITRE ID | IP Origen |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for a in alerts:
        mitre_ids = a.get("mitre_ids")
        mitre_str = ", ".join(mitre_ids) if isinstance(mitre_ids, list) else (mitre_ids or "-")
        lines.append(
            "| {ts} | {agent} | {level} | {rule} | {desc} | {mitre} | {srcip} |".format(
                ts=a.get("timestamp", ""),
                agent=a.get("agent", "") or "-",
                level=a.get("level", ""),
                rule=a.get("rule_id", ""),
                desc=(a.get("description", "") or "").replace("|", "-"),
                mitre=mitre_str,
                srcip=a.get("srcip", "") or "-",
            )
        )
    lines.append("")
    return "\n".join(lines)


def mitre_coverage_to_markdown(data: dict) -> str:
    """Convierte la cobertura MITRE de Wazuh a Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hours = data.get("window_hours", 24)
    min_level = data.get("min_level", 0)
    total_techs = data.get("total_techniques", 0)
    techniques = data.get("techniques", []) or []
    tactics = data.get("tactics", []) or []

    lines = [
        "# Reporte de Cobertura MITRE ATT&CK (Wazuh)",
        "",
        f"- **Fecha:** {now}",
        f"- **Ventana temporal:** Últimas {hours} horas",
        f"- **Nivel mínimo:** {min_level}",
        f"- **Técnicas detectadas:** {total_techs}",
        "",
    ]

    if techniques:
        lines += [
            "## Técnicas Principales",
            "",
            "| ID | Nombre | Tácticas | Conteo | Deprecated |",
            "| --- | --- | --- | --- | --- |",
        ]
        for t in techniques:
            tactics_str = ", ".join(t.get("tactics", []) or []) or "-"
            name = t.get("name") or "-"
            url = t.get("url")
            id_cell = f"[{t.get('id')}]({url})" if url else t.get("id", "")
            dep = "Sí" if t.get("deprecated") else "No"
            lines.append(
                f"| {id_cell} | {name} | {tactics_str} | {t.get('count', 0)} | {dep} |"
            )
        lines.append("")

    if tactics:
        lines += [
            "## Tácticas",
            "",
            "| Táctica | Conteo de Alertas |",
            "| --- | --- |",
        ]
        for tac in tactics:
            lines.append(f"| {tac.get('tactic', '')} | {tac.get('count', 0)} |")
        lines.append("")

    return "\n".join(lines)


def mitre_search_to_markdown(data: dict) -> str:
    """Convierte resultados de búsqueda RAG de MITRE ATT&CK a Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = data.get("query", "")
    results = data.get("results", []) or []

    lines = [
        "# Reporte de Búsqueda MITRE ATT&CK (RAG)",
        "",
        f"- **Fecha:** {now}",
        f"- **Consulta:** `{query}`",
        f"- **Resultados:** {len(results)}",
        "",
    ]

    if not results:
        lines.append("_No se encontraron técnicas._")
        return "\n".join(lines) + "\n"

    for r in results:
        url = r.get("url")
        tid = r.get("id", "")
        name = r.get("name", "")
        title = f"[{tid} - {name}]({url})" if url else f"{tid} - {name}"
        lines += [
            f"## {title}",
            "",
            f"- **Tácticas:** {r.get('tactics', '-')}",
            "",
            "### Extracto",
            "",
            f"> {r.get('excerpt', '').strip().replace(chr(10), ' ')}",
            "",
        ]

    return "\n".join(lines)


def _sanitize(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "").strip())
    return safe.strip("._-") or "scan"


def save_markdown_report(data: dict, reports_dir: str = "reports") -> str:
    """Escribe el reporte Markdown en reports/ y devuelve la ruta generada (Nmap legacy)."""
    os.makedirs(reports_dir, exist_ok=True)
    target = _sanitize(data.get("target", "scan"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(reports_dir, f"nmap_{target}_{timestamp}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(scan_to_markdown(data))
    return path


def save_general_markdown_report(content: str, prefix: str, reports_dir: str = "reports") -> str:
    """Escribe un reporte Markdown general en reports/ y devuelve la ruta generada."""
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(reports_dir, f"{prefix}_{timestamp}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path
