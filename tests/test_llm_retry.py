"""Tests del reintento ante fallos de conexión y de la configuración del LLM.

Se usan modelos falsos y `sleep` inyectado para que no haya red ni esperas.
"""

import os
import subprocess
import sys

import pytest
from langchain_core.exceptions import ModelConnectionError

from capazeta.llm import (
    LLMConfigurationError,
    LLMConnectionError,
    invoke_with_retry,
    validar_credenciales,
)


class ModeloFalso:
    """Modelo que falla las primeras `fallos` veces y luego responde."""

    def __init__(self, fallos=0, respuesta="respuesta OK", excepcion=None):
        self.fallos = fallos
        self.respuesta = respuesta
        self.excepcion = excepcion or ModelConnectionError("sin conexión")
        self.llamadas = 0

    def invoke(self, messages):
        self.llamadas += 1
        if self.llamadas <= self.fallos:
            raise self.excepcion
        return self.respuesta


def _sin_espera(_segundos):
    pass


def test_exito_al_primer_intento_no_reintentar():
    modelo = ModeloFalso(fallos=0)
    eventos = []

    resultado = invoke_with_retry(
        modelo, ["hola"], sleep=_sin_espera, on_retry=lambda *args: eventos.append(args)
    )

    assert resultado == "respuesta OK"
    assert modelo.llamadas == 1
    assert eventos == []


def test_falla_dos_veces_y_responde_en_el_tercero():
    modelo = ModeloFalso(fallos=2)
    eventos = []

    resultado = invoke_with_retry(
        modelo, ["hola"], sleep=_sin_espera, on_retry=lambda *args: eventos.append(args)
    )

    assert resultado == "respuesta OK"
    assert modelo.llamadas == 3
    assert [intento for intento, _, _ in eventos] == [1, 2]
    assert [espera for _, espera, _ in eventos] == [1.0, 2.0]


def test_agota_los_tres_intentos_y_avisa_al_usuario(monkeypatch):
    clave = "sk-clave-secreta-de-prueba-1234567890"
    monkeypatch.setenv("OPENAI_API_KEY", clave)
    modelo = ModeloFalso(fallos=3, excepcion=ModelConnectionError(f"fallo con {clave}"))

    with pytest.raises(LLMConnectionError) as info:
        invoke_with_retry(modelo, ["hola"], sleep=_sin_espera)

    assert modelo.llamadas == 3
    mensaje = str(info.value)
    assert "3 intentos" in mensaje
    assert clave not in mensaje
    assert "<REDACTADO>" in mensaje


def test_error_no_reintentable_se_propaga():
    class ModeloConErrorDeCodigo:
        def __init__(self):
            self.llamadas = 0

        def invoke(self, mensajes):
            self.llamadas += 1
            raise ValueError("error de código")

    modelo = ModeloConErrorDeCodigo()

    with pytest.raises(ValueError, match="error de código"):
        invoke_with_retry(modelo, ["hola"], sleep=_sin_espera)

    assert modelo.llamadas == 1


@pytest.mark.parametrize(
    ("modelo", "variable"),
    [
        ("openai:gpt-4o-mini", "OPENAI_API_KEY"),
        ("groq:openai/gpt-oss-120b", "GROQ_API_KEY"),
        ("google_genai:gemini-3.1-flash-lite", "GOOGLE_API_KEY"),
    ],
)
def test_api_key_vacia_falla_antes_de_inicializar(monkeypatch, modelo, variable):
    monkeypatch.setenv(variable, "")

    with pytest.raises(LLMConfigurationError) as info:
        validar_credenciales(modelo)

    mensaje = str(info.value)
    assert variable in mensaje
    assert modelo in mensaje
    assert "Traceback" not in mensaje


def test_api_key_presente_pasa_la_validacion(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-clave-ficticia-de-prueba")

    assert validar_credenciales("openai:gpt-4o-mini") is None


def test_cli_con_api_key_vacia_sale_sin_traceback():
    entorno = os.environ.copy()
    entorno.update(
        {
            "MODEL_NAME": "openai:gpt-4o-mini",
            "OPENAI_API_KEY": "",
            "COLUMNS": "200",
        }
    )

    resultado = subprocess.run(
        [sys.executable, "-m", "capazeta.main"],
        env=entorno,
        input="",
        capture_output=True,
        text=True,
        timeout=60,
    )
    salida = resultado.stdout + resultado.stderr

    assert resultado.returncode == 1
    assert "Falta la variable OPENAI_API_KEY" in salida
    assert "Traceback" not in salida
