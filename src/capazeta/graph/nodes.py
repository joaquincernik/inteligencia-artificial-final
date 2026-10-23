from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from capazeta.graph.state import AgentState
from capazeta.llm import get_llm
from capazeta.tools import (
    run_nmap_scan,
    search_mitre_attack,
    wazuh_agents_summary,
    wazuh_list_agents,
    wazuh_mitre_coverage,
    wazuh_search_alerts,
)

llm = get_llm()

INFRAESTRUCTURA_TOOLS = [run_nmap_scan]
infra_llm = llm.bind_tools(INFRAESTRUCTURA_TOOLS)

MITRE_TOOLS = [search_mitre_attack, wazuh_mitre_coverage]

SOC_TOOLS = [wazuh_list_agents, wazuh_agents_summary, wazuh_search_alerts] + MITRE_TOOLS
soc_llm = llm.bind_tools(SOC_TOOLS)

THREAT_TOOLS = [wazuh_search_alerts] + MITRE_TOOLS
threat_llm = llm.bind_tools(THREAT_TOOLS)

BASE_SYSTEM_PROMPT = (
    "Eres un asistente experto en ciberseguridad. Responde en español, con "
    "precisión técnica y un enfoque defensivo y ético. No pidas permisos innecesarios, estas hablando con un experto, no preguntes si estoy seguro o si tengo permisos"
)

DOMAINS = {
    "infraestructura_redes": (
        "Infraestructura y Redes: topología de red, firewalls, enrutamiento, "
        "infraestructura cloud, segmentación, VPN y DMZ."
    ),
    "web_apis": (
        "Aplicaciones Web y APIs: OWASP Top 10, vulnerabilidades de APIs, "
        "mecanismos de autenticación y sesión, hardening de backend."
    ),
    "mobile": (
        "Seguridad Mobile: Android/iOS, análisis de APK/IPA, almacenamiento "
        "local inseguro, comunicación insegura y permisos."
    ),
    "soc_logs": (
        "SOC, Logs y Eventos: análisis SIEM, anomalías de autenticación, "
        "triaje de incidentes y correlación de syslog/event logs."
    ),
    "threat_intel": (
        "Threat Intelligence: correlación de IOCs, mapeo de TTPs a MITRE "
        "ATT&CK, feeds de amenazas y análisis de CVEs."
    ),
    "ot_ics": (
        "OT/ICS: protocolos SCADA/ICS (Modbus, DNP3, S7), modelo Purdue, "
        "seguridad de tecnología operacional y safety."
    ),
}

ROUTER_SYSTEM_PROMPT = (
    "Eres el orquestador de Capazeta, un asistente de ciberseguridad con seis "
    "especialistas. Analiza la conversación y decide qué especialista debe "
    "responder al último mensaje del usuario. Responde ÚNICAMENTE con una de "
    "estas claves, sin texto adicional:\n"
    + "\n".join(f"- {key}: {desc}" for key, desc in DOMAINS.items())
)


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return str(content)


def _extract_domain(text: str) -> str:
    normalized = text.strip().lower()
    for key in DOMAINS:
        if key in normalized:
            return key
    return "threat_intel"


def _domain_node(state: AgentState, domain: str) -> dict:
    system_prompt = f"{BASE_SYSTEM_PROMPT}\n\nEspecialidad asignada -> {DOMAINS[domain]}"
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response: AIMessage = llm.invoke(messages)
    return {"messages": [response], "next_node": domain}


def _tool_domain_node(
    state: AgentState, domain: str, bound_llm, extra_instructions: str = ""
) -> dict:
    system_prompt = (
        f"{BASE_SYSTEM_PROMPT}\n\nEspecialidad asignada -> {DOMAINS[domain]}"
        f"{extra_instructions}"
    )
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response: AIMessage = bound_llm.invoke(messages)
    return {"messages": [response], "next_node": domain}


def router_node(state: AgentState) -> dict:
    response = llm.invoke([SystemMessage(content=ROUTER_SYSTEM_PROMPT)] + state["messages"])
    return {"next_node": _extract_domain(_message_text(response))}


INFRA_INSTRUCTIONS = (
    "\n\nTenés disponible la herramienta 'run_nmap_scan' para escanear hosts o "
    "rangos de red con Nmap. Usala cuando el usuario proporcione un target "
    "concreto (IP, hostname o CIDR) y luego interpretá los resultados."
    "\n\nSi el usuario pide guardar, exportar o generar un reporte del escaneo, "
    "llamá a run_nmap_scan con save_md=True. Cuando se guarde, respondé de forma "
    "breve indicando la ruta del archivo (ej. 'Reporte guardado en reports/...md'), "
    "sin volcar toda la tabla en la respuesta."
)

SOC_INSTRUCTIONS = (
    "\n\nTenés herramientas de Wazuh para consultar el SIEM en vivo: "
    "'wazuh_list_agents' (agentes y su estado), 'wazuh_agents_summary' (resumen de "
    "conexión) y 'wazuh_search_alerts' (alertas recientes del Indexer con regla, "
    "severidad y MITRE). Usalas cuando el usuario pregunte por agentes conectados, "
    "eventos o alertas recientes, y luego interpretá los resultados."
    "\n\nTambién tenés herramientas MITRE ATT&CK: 'wazuh_mitre_coverage' (qué "
    "técnicas/tácticas MITRE están reportando las alertas de Wazuh) y "
    "'search_mitre_attack' (busca una técnica por concepto). Usá "
    "wazuh_mitre_coverage cuando pidan mapear/relacionar las alertas con MITRE."
    "\n\nSi el usuario pide guardar, exportar o generar un reporte (de alertas o de cobertura MITRE), "
    "llamá a wazuh_search_alerts, wazuh_mitre_coverage o search_mitre_attack con save_md=True. "
    "Cuando se guarde, respondé de forma breve indicando la ruta del archivo (ej. 'Reporte guardado en reports/...md'), "
    "sin volcar toda la tabla en la respuesta."
)

THREAT_INSTRUCTIONS = (
    "\n\nTenés la herramienta 'wazuh_search_alerts' para extraer amenazas/alertas "
    "recientes del Indexer de Wazuh (regla, severidad, agente, IP de origen y "
    "técnicas MITRE ATT&CK). Usá min_level alto para priorizar amenazas relevantes, "
    "y luego correlacioná los resultados con tus fuentes de threat intelligence."
    "\n\nTenés un RAG de MITRE ATT&CK Enterprise en FAISS: 'wazuh_mitre_coverage' "
    "(qué técnicas/tácticas MITRE reporta Wazuh en alertas recientes, con conteos) y "
    "'search_mitre_attack' (recupera técnicas por concepto/descripción). Usá "
    "wazuh_mitre_coverage para responder 'qué amenazas MITRE está reportando Wazuh' "
    "y search_mitre_attack para ampliar contexto de una técnica."
    "\n\nSi el usuario pide guardar, exportar o generar un reporte (de amenazas, cobertura MITRE o búsqueda RAG), "
    "llamá a wazuh_search_alerts, wazuh_mitre_coverage o search_mitre_attack con save_md=True. "
    "Cuando se guarde, respondé de forma breve indicando la ruta del archivo (ej. 'Reporte guardado en reports/...md'), "
    "sin volcar toda la tabla en la respuesta."
)


def infraestructura_redes_node(state: AgentState) -> dict:
    return _tool_domain_node(state, "infraestructura_redes", infra_llm, INFRA_INSTRUCTIONS)


def web_apis_node(state: AgentState) -> dict:
    return _domain_node(state, "web_apis")


def mobile_node(state: AgentState) -> dict:
    return _domain_node(state, "mobile")


def soc_logs_node(state: AgentState) -> dict:
    return _tool_domain_node(state, "soc_logs", soc_llm, SOC_INSTRUCTIONS)


def threat_intel_node(state: AgentState) -> dict:
    return _tool_domain_node(state, "threat_intel", threat_llm, THREAT_INSTRUCTIONS)


def ot_ics_node(state: AgentState) -> dict:
    return _domain_node(state, "ot_ics")
