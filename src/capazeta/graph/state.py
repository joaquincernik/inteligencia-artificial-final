from typing import Optional
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    next_node: Optional[str]
    domain_context: Optional[str]
    findings: Optional[list[str]]
