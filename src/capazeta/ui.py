"""Capa de presentación de la CLI de Capazeta (Rich).

Centraliza la consola compartida y los helpers de salida para que `main.py` y las
tools muestren un formato consistente. Las respuestas de los agentes llegan en
Markdown y se renderizan con `rich.markdown.Markdown`.
"""
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

AGENT_LABELS = {
    "infraestructura_redes": "Infraestructura y Redes",
    "web_apis": "Aplicaciones Web y APIs",
    "mobile": "Mobile",
    "soc_logs": "SOC / Logs y Eventos",
    "threat_intel": "Threat Intelligence",
    "ot_ics": "OT/ICS",
}

ACCENT = "cyan"
EXIT_COMMANDS = {"salir", "exit", "quit", "/exit", "/salir", ":q"}


def label_for(node: str | None) -> str:
    """Devuelve la etiqueta legible del subagente que respondió."""
    return AGENT_LABELS.get(node or "", node or "Desconocido")


def _fmt_tokens(value) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def print_banner(model: str, thread_id: str) -> None:
    """Banner de inicio con modelo, thread y ayuda de comandos."""
    body = Text()
    body.append("modelo  ", style="dim")
    body.append(model, style="bold")
    body.append("\n")
    body.append("thread  ", style="dim")
    body.append(thread_id, style="bold")
    body.append("\n")
    body.append("salir   ", style="dim")
    body.append("salir · Ctrl+C · Ctrl+D", style="bold")
    console.print(
        Panel(
            body,
            title="[bold cyan]🛡️  Capazeta[/]",
            subtitle="[dim]asistente multi-agente de ciberseguridad[/]",
            border_style=ACCENT,
            padding=(1, 2),
        )
    )


def print_diagram_status(ok: bool, detail: str) -> None:
    """Informa el resultado de exportar el diagrama Mermaid del grafo."""
    if ok:
        console.print(f"🖼️  Diagrama del grafo actualizado en [bold]{detail}[/]")
    else:
        console.print(f"[yellow]⚠️  No se pudo generar el diagrama del grafo:[/] {detail}")


def print_response(text: str, agent_label: str) -> None:
    """Renderiza la respuesta en Markdown dentro de un panel con el agente."""
    if not (text or "").strip():
        console.print(
            Panel(
                "[yellow]El agente no devolvió texto (posible corte del bucle de "
                "herramientas).[/]",
                title=f"[bold]{agent_label}[/]",
                border_style="yellow",
                padding=(0, 2),
            )
        )
        return
    console.print(
        Panel(
            Markdown(text),
            title=f"[bold]{agent_label}[/]",
            border_style=ACCENT,
            padding=(0, 2),
        )
    )


def print_metrics(
    input_tokens, output_tokens, interaction_tokens, accumulated_tokens
) -> None:
    """Muestra los tokens de la interacción y el acumulado de la sesión."""
    table = Table.grid(padding=(0, 2))
    table.add_row(
        Text(f"entrada {_fmt_tokens(input_tokens)}", style="dim"),
        Text(f"salida {_fmt_tokens(output_tokens)}", style="dim"),
        Text(f"total {_fmt_tokens(interaction_tokens)}", style="bold"),
        Text(f"sesión {_fmt_tokens(accumulated_tokens)}", style="bold cyan"),
    )
    console.print(Text("─" * min(console.width, 70), style="dim"))
    console.print(table)
    console.print()


def print_error(message: str) -> None:
    """Línea de error sin traceback."""
    console.print(f"[bold red]✖[/] {message}")


def print_goodbye() -> None:
    """Cierre ordenado de la sesión."""
    console.print("\n[dim]Hasta la próxima 👋[/]\n")


def progress(message: str) -> None:
    """Mensaje de progreso; se imprime por encima del spinner activo."""
    console.print(Text(f"  › {message}", style="dim"))


def status(message: str):
    """Spinner para envolver operaciones lentas: `with status('...'):`."""
    return console.status(f"[{ACCENT}]{message}[/]", spinner="dots", refresh_per_second=8)
