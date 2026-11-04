from langchain_core.messages import AIMessage, HumanMessage

from capazeta import ui
from capazeta.config import MODEL_NAME, THREAD_ID
from capazeta.graph.builder import build_graph

DIAGRAM_PATH = "docs/img/grafico.png"


def _content_to_text(content) -> str:
    """Extrae el texto de un mensaje (str o lista de bloques de contenido)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict):
            parts.append(block.get("text") or "")
        else:
            parts.append(str(block))
    return "\n".join(part for part in parts if part).strip()


def main():
    graph = build_graph()

    # Generar la imagen del diagrama de LangGraph
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=DIAGRAM_PATH)
        ui.print_diagram_status(True, DIAGRAM_PATH)
    except Exception as exc:
        ui.print_diagram_status(False, str(exc))

    config = {
        "configurable": {"thread_id": THREAD_ID},
        "tags": [f"model:{MODEL_NAME}"],
        "metadata": {"model": MODEL_NAME, "thread_id": THREAD_ID},
        "run_name": "capazeta",
    }
    total_tokens_acumulados = 0

    ui.print_banner(MODEL_NAME, THREAD_ID)

    while True:
        try:
            user_input = ui.console.input("[bold cyan]vos ❯[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            ui.print_goodbye()
            break

        if not user_input:
            ui.console.print("[dim]Escribí una consulta o 'salir' para terminar.[/]")
            continue
        if user_input.lower() in ui.EXIT_COMMANDS:
            ui.print_goodbye()
            break

        user_message = HumanMessage(content=user_input)
        try:
            with ui.status("Analizando la consulta..."):
                response = graph.invoke({"messages": [user_message]}, config=config)
        except KeyboardInterrupt:
            ui.print_error("Consulta cancelada.")
            continue
        except Exception as exc:
            ui.print_error(f"Error al procesar la consulta: {exc}")
            continue

        last_message: AIMessage = response["messages"][-1]
        text = _content_to_text(last_message.content)
        node = response.get("next_node")
        agent_label = ui.label_for(node)

        ui.print_response(text, agent_label)

        usage = last_message.usage_metadata or {}
        tokens_entrada = usage.get("input_tokens", 0)
        tokens_salida = usage.get("output_tokens", 0)
        tokens_interaccion = usage.get("total_tokens", 0)
        total_tokens_acumulados += tokens_interaccion

        ui.print_metrics(
            tokens_entrada, tokens_salida, tokens_interaccion, total_tokens_acumulados
        )


if __name__ == "__main__":
    main()
