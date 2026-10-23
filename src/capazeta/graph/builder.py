from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from capazeta.graph.nodes import (
    router_node,
    infraestructura_redes_node,
    web_apis_node,
    mobile_node,
    soc_logs_node,
    threat_intel_node,
    ot_ics_node,
)
from capazeta.graph.state import AgentState
from capazeta.tools import (
    run_nmap_scan,
    search_mitre_attack,
    wazuh_agents_summary,
    wazuh_list_agents,
    wazuh_mitre_coverage,
    wazuh_search_alerts,
)

DOMAIN_NODES = [
    "infraestructura_redes",
    "web_apis",
    "mobile",
    "soc_logs",
    "threat_intel",
    "ot_ics",
]

TOOL_DOMAINS = {
    "infraestructura_redes": "infra_tools",
    "soc_logs": "soc_tools",
    "threat_intel": "threat_tools",
}


def route_decision(state: AgentState) -> str:
    return state.get("next_node") or "threat_intel"


def build_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("router", router_node)
    graph_builder.add_node("infraestructura_redes", infraestructura_redes_node)
    graph_builder.add_node("web_apis", web_apis_node)
    graph_builder.add_node("mobile", mobile_node)
    graph_builder.add_node("soc_logs", soc_logs_node)
    graph_builder.add_node("threat_intel", threat_intel_node)
    graph_builder.add_node("ot_ics", ot_ics_node)

    graph_builder.add_node("infra_tools", ToolNode([run_nmap_scan]))
    graph_builder.add_node(
        "soc_tools",
        ToolNode(
            [
                wazuh_list_agents,
                wazuh_agents_summary,
                wazuh_search_alerts,
                search_mitre_attack,
                wazuh_mitre_coverage,
            ]
        ),
    )
    graph_builder.add_node(
        "threat_tools",
        ToolNode([wazuh_search_alerts, search_mitre_attack, wazuh_mitre_coverage]),
    )

    graph_builder.add_edge(START, "router")
    graph_builder.add_conditional_edges("router", route_decision, DOMAIN_NODES)

    for node in DOMAIN_NODES:
        if node in TOOL_DOMAINS:
            continue
        graph_builder.add_edge(node, END)

    for domain, tool_node in TOOL_DOMAINS.items():
        graph_builder.add_conditional_edges(
            domain,
            tools_condition,
            {"tools": tool_node, END: END},
        )
        graph_builder.add_edge(tool_node, domain)

    checkpointer = InMemorySaver()
    return graph_builder.compile(checkpointer=checkpointer)
