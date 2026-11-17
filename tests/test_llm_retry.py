"""Tests del reintento ante fallos de conexión del LLM.

Se usan modelos falsos y `sleep` inyectado para que no haya red ni esperas.
"""

import pytest
from langchain_core.exceptions import ModelConnectionError

from capazeta.llm import LLMConnectionError, invoke_with_retry


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
