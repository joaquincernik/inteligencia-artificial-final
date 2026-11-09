from langchain.chat_models import init_chat_model
from capazeta.config import LLM_SEED, LLM_TEMPERATURE, MODEL_NAME


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
