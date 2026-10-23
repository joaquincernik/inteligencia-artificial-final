"""Herramientas de Wazuh para los subagentes de SOC y Threat Intelligence.

- Agentes conectados: API de Wazuh (por defecto https://localhost:55000).
- Alertas/threats recientes: Indexer de Wazuh/OpenSearch (por defecto https://localhost:9200).
"""
import json
import time

import httpx
from langchain_core.tools import tool

from capazeta.config import (
    WAZUH_API_PASSWORD,
    WAZUH_API_URL,
    WAZUH_API_USER,
    WAZUH_INDEXER_PASSWORD,
    WAZUH_INDEXER_URL,
    WAZUH_INDEXER_USER,
    WAZUH_VERIFY_SSL,
)
from capazeta.tools.report import (
    save_general_markdown_report,
    wazuh_alerts_to_markdown,
)

_token_cache = {"token": None, "expires_at": 0.0}


def _client(timeout: float = 15.0) -> httpx.Client:
    return httpx.Client(verify=WAZUH_VERIFY_SSL, timeout=timeout)


def _api_token(client: httpx.Client) -> str:
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]
    if not WAZUH_API_PASSWORD:
        raise RuntimeError(
            "Falta WAZUH_API_PASSWORD en .env (contraseña de la API de Wazuh)."
        )
    response = client.post(
        f"{WAZUH_API_URL}/security/user/authenticate",
        auth=(WAZUH_API_USER, WAZUH_API_PASSWORD),
    )
    response.raise_for_status()
    payload = response.json()
    token = (payload.get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No se obtuvo token de la API de Wazuh: {payload}")
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 600  # margen sobre los 900s por defecto
    return token


def _api_get(path: str, params: dict | None = None) -> dict:
    with _client() as client:
        token = _api_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get(f"{WAZUH_API_URL}{path}", params=params, headers=headers)
        if response.status_code == 401:
            _token_cache["token"] = None
            token = _api_token(client)
            response = client.get(
                f"{WAZUH_API_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        return response.json()


def _indexer_search(index: str, body: dict) -> dict:
    if not WAZUH_INDEXER_PASSWORD:
        raise RuntimeError(
            "Falta WAZUH_INDEXER_PASSWORD en .env (contraseña del Indexer de Wazuh)."
        )
    with _client(timeout=30.0) as client:
        response = client.post(
            f"{WAZUH_INDEXER_URL}/{index}/_search",
            auth=(WAZUH_INDEXER_USER, WAZUH_INDEXER_PASSWORD),
            json=body,
        )
        response.raise_for_status()
        return response.json()


@tool
def wazuh_list_agents(status: str = "active", limit: int = 50) -> str:
    """Lista los agentes registrados en Wazuh (id, nombre, IP, SO, estado y último keep alive).

    Args:
        status: Filtra por estado ("active", "disconnected", "pending", "never_connected").
            Dejar vacío ("") para listar todos.
        limit: Cantidad máxima de agentes a devolver.
    """
    print("consultando wazuh...", flush=True)
    params: dict = {"limit": limit, "sort": "+name"}
    if status:
        params["status"] = status
    try:
        payload = _api_get("/agents", params=params)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    data = payload.get("data") or {}
    agentes = [
        {
            "id": agent.get("id"),
            "name": agent.get("name"),
            "ip": agent.get("ip"),
            "status": agent.get("status"),
            "os": (agent.get("os") or {}).get("name"),
            "version": agent.get("version"),
            "lastKeepAlive": agent.get("lastKeepAlive"),
        }
        for agent in data.get("affected_items", [])
    ]
    return json.dumps(
        {"total": data.get("total_affected_items", len(agentes)), "agents": agentes},
        ensure_ascii=False,
    )


@tool
def wazuh_agents_summary() -> str:
    """Devuelve el resumen de conexión de agentes de Wazuh (active, disconnected, pending, etc.)."""
    print("consultando wazuh...", flush=True)
    try:
        payload = _api_get("/agents/summary/status")
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps(payload.get("data") or {}, ensure_ascii=False)


@tool
def wazuh_search_alerts(
    limit: int = 20, min_level: int = 0, hours: int = 24, save_md: bool = False
) -> str:
    """Busca alertas recientes de Wazuh en el Indexer (regla, severidad, agente y MITRE ATT&CK).

    Args:
        limit: Cantidad máxima de alertas a devolver.
        min_level: Nivel mínimo de la regla (0-15); usar >= 7 para amenazas relevantes.
        hours: Ventana temporal hacia atrás en horas.
        save_md: Si es True, guarda un reporte Markdown en reports/.
    """
    print("consultando wazuh...", flush=True)
    body = {
        "size": limit,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "filter": [
                    {"range": {"rule.level": {"gte": min_level}}},
                    {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
                ]
            }
        },
        "_source": [
            "@timestamp",
            "agent.name",
            "agent.ip",
            "rule.id",
            "rule.level",
            "rule.description",
            "rule.mitre.id",
            "rule.mitre.technique",
            "data.srcip",
        ],
    }
    try:
        payload = _indexer_search("wazuh-alerts-*", body)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    hits = (payload.get("hits") or {}).get("hits", [])
    total_raw = (payload.get("hits") or {}).get("total", len(hits))
    total = total_raw.get("value") if isinstance(total_raw, dict) else total_raw

    alerts = []
    for hit in hits:
        src = hit.get("_source") or {}
        rule = src.get("rule") or {}
        agent = src.get("agent") or {}
        mitre = rule.get("mitre") or {}
        alerts.append(
            {
                "timestamp": src.get("@timestamp"),
                "agent": agent.get("name"),
                "agent_ip": agent.get("ip"),
                "rule_id": rule.get("id"),
                "level": rule.get("level"),
                "description": rule.get("description"),
                "mitre_ids": mitre.get("id"),
                "mitre_techniques": mitre.get("technique"),
                "srcip": (src.get("data") or {}).get("srcip"),
            }
        )
    result_data = {"total": total, "alerts": alerts}
    if save_md:
        md_content = wazuh_alerts_to_markdown(result_data)
        result_data["file"] = save_general_markdown_report(md_content, "wazuh_alerts")
    return json.dumps(result_data, ensure_ascii=False)
