from langchain_core.messages import HumanMessage, AIMessage
from capazeta.config import THREAD_ID, MODEL_NAME
from capazeta.graph.builder import build_graph

AGENT_LABELS = {
    "infraestructura_redes": "Infraestructura y Redes",
    "web_apis": "Aplicaciones Web y APIs",
    "mobile": "Mobile",
    "soc_logs": "SOC / Logs y Eventos",
    "threat_intel": "Threat Intelligence",
    "ot_ics": "OT/ICS",
}

def main():
    graph = build_graph()
    # Generar la imagen del diagrama de LangGraph
    try:
        graph.get_graph().draw_mermaid_png(output_file_path='docs/img/grafico.png')
        print("🖼️ Diagrama del grafo actualizado en 'docs/img/grafico.png'")
    except Exception as e:
        print(f"⚠️ No se pudo generar la imagen del grafo: {e}")

    config = {'configurable': {'thread_id': THREAD_ID, "tags": [f"model:{MODEL_NAME}"]}}
    total_tokens_acumulados = 0

    print("\n--- Agente Capazeta Iniciado ---\n")

    while True:
        try:
            user_input = input("Enter your message: ")
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ["exit", "quit", "salir"]:
                print("👋 Saliendo de Capazeta...")
                break
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Saliendo de Capazeta...")
            break

        user_message = HumanMessage(content=user_input)
        response = graph.invoke({'messages': [user_message]}, config=config)

        last_message: AIMessage = response['messages'][-1]
        content = last_message.content
        text = content if isinstance(content, str) else content[0]['text']
        node = response.get('next_node')
        agent_label = AGENT_LABELS.get(node, node or "Desconocido")

        print(f"\n{agent_label} Agent Response:\n{text}")
        usage = last_message.usage_metadata or {}
        tokens_entrada = usage.get('input_tokens', 0)
        tokens_salida = usage.get('output_tokens', 0)
        tokens_interaccion = usage.get('total_tokens', 0)
        
        print("\n" + "-" * 50)
        print(f"📊 Interacción actual: {tokens_interaccion} tokens (Entrada: {tokens_entrada} | Salida: {tokens_salida})")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    main()
