"""Inicialización de modelos de chat y reintento ante fallos de conexión.

La lógica de `invoke_with_retry` responde a una pregunta del docente durante la
exposición: si la conexión con el proveedor del LLM falla, se reintentan hasta
3 veces con espera exponencial y, si el error persiste, se informa al usuario
con un mensaje claro en lugar de mostrar un traceback.
"""

import os
import re
import time

from langchain.chat_models import init_chat_model
from langchain_core.exceptions import ModelError

from capazeta.config import (
    LLM_MAX_RETRIES,
    LLM_RETRY_DELAY,
    LLM_SEED,
    LLM_TEMPERATURE,
    MODEL_NAME,
)

_SECRET_ENV_VARS = (
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
    "CLOUDFLARE_API_TOKEN",
)


def _redactar(texto: str) -> str:
    """Quita API keys del texto antes de mostrárselo al usuario."""
    if not texto:
        return ""
    for nombre in _SECRET_ENV_VARS:
        valor = os.getenv(nombre)
        if valor and len(valor) >= 8:
            texto = texto.replace(valor, "<REDACTADO>")
    return re.sub(r"sk-[A-Za-z0-9_-]{4,}", "<REDACTADO>", texto)


class LLMConnectionError(RuntimeError):
    """Error presentable al usuario cuando el LLM no responde tras reintentar."""

    def __init__(self, intentos: int, causa: Exception | str):
        self.intentos = intentos
        super().__init__(
            f"No se pudo conectar con el modelo de lenguaje después de "
            f"{intentos} intentos. Revisá tu conexión y la configuración de la "
            f"API key, o intentá de nuevo en unos minutos. "
            f"Detalle: {_redactar(str(causa))}"
        )


def invoke_with_retry(
    llm,
    messages,
    *,
    max_retries: int | None = None,
    base_delay: float | None = None,
    sleep=time.sleep,
    on_retry=None,
):
    """Invoca el LLM reintentando errores de modelo/red con backoff exponencial.

    ``sleep`` y ``on_retry`` se pueden inyectar para que las pruebas y el
    notebook de demostración sean rápidos y puedan reportar cada intento.
    """
    intentos = max_retries if max_retries is not None else LLM_MAX_RETRIES
    delay = base_delay if base_delay is not None else LLM_RETRY_DELAY
    ultima_exc: Exception | None = None

    for intento in range(1, intentos + 1):
        try:
            return llm.invoke(messages)
        except (ModelError, ConnectionError, TimeoutError) as exc:
            ultima_exc = exc
            if intento == intentos:
                break
            espera = delay * (2 ** (intento - 1))
            if on_retry is not None:
                on_retry(intento, espera, exc)
            sleep(espera)

    raise LLMConnectionError(intentos, ultima_exc) from ultima_exc


def _seed_kwargs(provider: str) -> dict:
    """Aplica la semilla según el proveedor del modelo configurado."""
    if provider in {"google_genai", "openai"}:
        return {"seed": LLM_SEED}
    # ChatGroq no expone `seed` como campo propio, pero la API de Groq lo acepta
    # como parámetro del modelo.
    if provider == "groq":
        return {"model_kwargs": {"seed": LLM_SEED}}
    return {}


def get_llm():
    provider = MODEL_NAME.split(":", 1)[0].strip()
    return init_chat_model(
        MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        **_seed_kwargs(provider),
    )
