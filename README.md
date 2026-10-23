<div align="center">

# Capazeta agent

### Asistente ciberseguridad multi-agente modular basado en LangGraph y LangChain

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-en%20desarrollo-orange.svg)]()

</div>

---

## 📋 Tabla de contenidos

- [Demo](#-demo)
- [Sobre el proyecto](#-sobre-el-proyecto)
  - [Contexto académico](#contexto-académico)
  - [Construido con](#construido-con)
- [El dataset](#-el-dataset)
- [Metodología](#-metodología)
- [Resultados](#-resultados)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Roadmap](#-roadmap)
- [Autores](#-autores)
- [Licencia](#-licencia)
- [Agradecimientos y referencias](#-agradecimientos-y-referencias)

---

## 🎬 Demo

![Diagrama del flujo de agentes](docs/img/grafico.png)

Capazeta se ejecuta de forma interactiva a través de una interfaz de línea de comandos (CLI) impulsada por `uv run capazeta`.

---

## 📖 Sobre el proyecto

**Capazeta** es un asistente cibernético multi-agente modular desarrollado con **LangGraph** y **LangChain**. Su propósito es ayudar a equipos de seguridad, administradores de red y analistas de SOC a realizar tareas de diagnóstico, análisis de vulnerabilidades, investigación de amenazas e interpretación de logs en tiempo real.

El sistema organiza sus capacidades en 6 nodos de subagentes especializados, coordinados por un enrutador principal:

1. **Infraestructura y Redes:** Análisis de topología de red, segmentación, firewalls y escaneo con Nmap.
2. **Aplicaciones Web y APIs:** Seguridad en aplicaciones web, OWASP Top 10, autenticación y hardening de APIs.
3. **Mobile:** Seguridad en plataformas Android/iOS, análisis de APKs/IPAs, almacenamiento local y comunicaciones.
4. **SOC / Logs y Eventos:** Análisis de SIEM, triaje de incidentes e integración con alertas de Wazuh.
5. **Threat Intelligence:** Mapeo de TTPs en MITRE ATT&CK mediante RAG (FAISS) e investigación de IOCs/CVEs.
6. **OT / ICS:** Protocolos de control industrial (Modbus, DNP3, S7), modelo Purdue y seguridad operacional.

### Contexto académico

- **Asignatura:** Inteligencia Artificial
- **Institución:** Instituto Universitario Aeronautico
- **Cohorte / año:** 2026
- **Docente:** Alexis Gonzalez

### Construido con

- [Python 3.10+](https://www.python.org/)
- [LangChain](https://www.langchain.com/) / [LangGraph](https://python.langchain.com/docs/langgraph/)
- [FAISS](https://github.com/facebookresearch/faiss) — Almacenamiento vectorial para RAG
- [Wazuh API & Indexer](https://wazuh.com/) — Integración con SIEM y gestión de alertas
- [python-nmap](https://xael.org/pages/python-nmap-en.html) — Automatización de escaneos de red
- [uv](https://docs.astral.sh/uv/) — Gestión rápida de entornos y dependencias

---

## 📊 El dataset

Capazeta utiliza la base de conocimiento oficial **MITRE ATT&CK Enterprise** para alimentar su módulo RAG (*Retrieval-Augmented Generation*).

| Campo | Detalle |
|---|---|
| Fuente | [MITRE ATT&CK Enterprise STIX Bundle](https://github.com/mitre-attack/attack-stix-data) |
| Formato | JSON / STIX 2.1 |
| Vector Index | FAISS (Índice vectorial generado con embeddings de Gemini) |
| Variables / Campos | IDs de técnicas, tácticas, descripciones, mitigaciones y referencias de TTPs |
| Licencia del dataset | Apache 2.0 (MITRE ATT&CK) |

---

## 🔬 Metodología

### Arquitectura Multi-Agente

Capazeta implementa un grafo direccionado de estados (`StateGraph`) respaldado por persitencia en memoria (`InMemorySaver`):

- **Router Central:** Clasifica el requerimiento del usuario y delega la tarea al subagente de dominio correspondiente.
- **Herramientas (ToolNodes):** Subagentes con capacidad de ejecución de herramientas iterativas (`infraestructura_redes`, `soc_logs`, `threat_intel`), utilizando bucles de Tool Calling para invocar escaneos Nmap, consultas al Indexer/API de Wazuh y búsquedas vectoriales sobre MITRE ATT&CK.

![Diagrama de Arquitectura](docs/img/grafico.png)

### Definición PEAS del agente

Para formalizar el comportamiento del sistema, se define Capazeta bajo el marco PEAS (Russell & Norvig):

| Elemento | Definición | Aplicación en Capazeta |
| :-- | :-- | :-- |
| **P - *Performance Measure* (Medida de rendimiento)** | Criterios para evaluar si el agente actúa correctamente. | Enrutamiento correcto al subagente, mapeo preciso a técnicas/tácticas MITRE ATT&CK, respuestas fundamentadas en el contexto recuperado, minimización de alucinaciones y utilidad de los reportes generados. |
| **E - *Environment* (Entorno)** | Espacio con el que interactúa el agente. | Consultas del usuario, stack de Wazuh (API/Indexer), objetivo de red para escaneo con Nmap, base de conocimiento MITRE ATT&CK, sistema de archivos local y herramientas disponibles. |
| **A - *Actuators* (Actuadores)** | Acciones que puede ejecutar del agente. | Respuestas al usuario, llamadas a herramientas (`run_nmap_scan`, `wazuh_list_agents`, `wazuh_search_alerts`, `wazuh_mitre_coverage`, `search_mitre_attack`), razonamiento entre subagentes y generación/guardado de reportes en Markdown. |
| **S - *Sensors* (Sensores)** | Percepciones que recibe del agente. | Mensajes del usuario, resultados de las herramientas ejecutadas, información recuperada del índice FAISS de MITRE ATT&CK, alertas/eventos de Wazuh, resultados de escaneo Nmap y estado del grafo (`AgentState`). |

### Sistema RAG (MITRE ATT&CK)

Las consultas sobre inteligencias de amenazas y cobertura de eventos se resuelven mediante búsqueda semántica contra un índice vectorial FAISS (`data/mitre/faiss`). Las técnicas y tácticas se parsean y sincronizan localmente desde el bundle de STIX.

---

## 📈 Resultados

### Estado actual (MVP)

El sistema se encuentra en etapa de **MVP funcional**. Se ha validado cualitativamente la correcta ejecución de las siguientes funcionalidades:

- **Enrutamiento multi-agente:** Clasificación correcta de las consultas hacia los 6 dominios de especialidad.
- **Herramientas activas:** Escaneo de red con Nmap, consulta de agentes/eventos/alertas desde Wazuh API/Indexer y generación automatizada de reportes en Markdown.
- **RAG MITRE ATT&CK:** Recuperación semántica de técnicas y tácticas desde el bundle STIX sobre un índice vectorial FAISS con embeddings de Gemini.
- **Arquitectura modular:** Grafo LangGraph con bucles de tool-calling y persistencia en memoria (`InMemorySaver`).

### Protocolo de evaluación para la entrega final

Para la siguiente etapa, se plantea la siguiente metodología de evaluación cuantitativa del desempeño del sistema:

#### 1. Calidad de Recuperación (*Retrieval*)
Se medirá si el sistema recupera las reglas o técnicas MITRE ATT&CK correctas frente a un log o alerta de Wazuh.

- **Hit Rate@K:** Porcentaje de consultas en las que al menos una técnica MITRE correcta se encuentra entre los top-K resultados recuperados.
- **Mean Reciprocal Rank (MRR):** Posición promedio de la primera respuesta correcta en el ranking de recuperación.
- **Recall@K:** Proporción de técnicas relevantes recuperadas respecto al total de técnicas esperadas para cada caso de prueba.

#### 2. Calidad de Generación (*LLM Generation*)
Se evaluará la respuesta final emitida por el agente para garantizar confiabilidad y evitar alucinaciones.

- **Fidelidad (*Faithfulness*):** Mide si todas las afirmaciones, tácticas o técnicas mencionadas en la respuesta se encuentran soportadas por el contexto recuperado por el RAG. Se busca minimizar alucinaciones.
- **Relevancia de la Respuesta (*Answer Relevance*):** Evalúa qué tan alineada se encuentra la respuesta con la consulta original y el objetivo del análisis solicitado.

Para automatizar estas métricas, se utilizarán frameworks de evaluación como [**Ragas**](https://docs.ragas.io/) integrados con [**LangSmith**](https://www.langchain.com/langsmith) para el seguimiento y trazabilidad de las evaluaciones.

#### 3. Baseline Comparativo
Se comparará el desempeño del sistema con un enfoque sin IA, tomando como referencia:

- **Búsqueda manual por analista SOC:** Tiempo promedio y precisión al mapear una alerta de Wazuh a sus técnicas correspondientes utilizando la documentación oficial de [MITRE ATT&CK](https://attack.mitre.org/).
- **Búsqueda tradicional por palabras clave:** Búsqueda sintáctica directa sobre el catálogo de técnicas MITRE (sin búsqueda vectorial semántica), evaluando también tiempo de resolución y precisión en el mapeo.

---

## 📂 Estructura del proyecto

```text
.
├── README.md
├── pyproject.toml
├── .gitignore
├── src/
│   └── capazeta/
│       ├── config.py           # Configuración de variables de entorno y parámetros
│       ├── embeddings.py       # Configuración del modelo de Embeddings
│       ├── llm.py              # Inicialización y abstracción de Chat Models
│       ├── main.py             # Bucle de interacción interactivo (CLI)
│       ├── graph/              # Grafo de estados, nodos y constructor de LangGraph
│       │   ├── builder.py
│       │   ├── nodes.py
│       │   └── state.py
│       ├── rag/                # Construcción y lectura de índice FAISS (MITRE)
│       │   ├── build.py
│       │   └── mitre.py
│       └── tools/              # Herramientas (Nmap, Wazuh, MITRE RAG, Reportes)
│           ├── firewall_tool.py
│           ├── mitre_tool.py
│           ├── nmap_tool.py
│           ├── report.py
│           └── wazuh_tool.py
├── data/
│   └── mitre/                  # Datos y catálogo de técnicas de MITRE ATT&CK
├── reports/                    # Salida de reportes generados (.md)
├── notebooks/                  # Notebooks de exploración y pruebas
├── tests/                      # Suite de pruebas unitarias/integración
└── docs/
    ├── index.html              # Página estática para GitHub Pages
    └── img/
        └── grafico.png         # Diagrama del grafo de agentes
```

---

## ⚙️ Instalación

### Prerrequisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git
- Python >= 3.10
- [Docker](https://www.docker.com/) y [Docker Compose](https://docs.docker.com/compose/) *(solo si vas a utilizar la integración con Wazuh)*

### Pasos

```bash
# 1. Cloná el repositorio
git clone https://https://github.com/joaquincernik/inteligencia-artificial-final

# 2. Creá el entorno virtual e instalá las dependencias con uv
uv venv --python 3.10
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 3. Sincronizá e instalá el proyecto en modo editable
uv sync
uv pip install -e .
```

### Configuración de Variables de Entorno

Copiá el archivo de ejemplo y completá con tus credenciales:

```bash
cp .env.example .env
```

Las variables principales son:

```env
GOOGLE_API_KEY=tu_api_key_aqui
MODEL_NAME=google_genai:gemini-2.5-flash-lite

# Configuración Wazuh
WAZUH_API_URL=https://localhost:55000
WAZUH_API_USER=admin
WAZUH_API_PASSWORD=tu_password_aqui
WAZUH_INDEXER_URL=https://localhost:9200
WAZUH_INDEXER_USER=admin
WAZUH_INDEXER_PASSWORD=tu_password_aqui
WAZUH_VERIFY_SSL=false
``` 

---

## Integración con Wazuh (Docker)

Capazeta cuenta con herramientas para consultar agentes, alertas y realizar mapeo a MITRE ATT&CK utilizando un stack de Wazuh. Para levantarlo localmente podés utilizar la configuración incluida en `infra/wazuh/`.

### Requisitos
- Docker y Docker Compose
- Mínimo 4GB de RAM libres (recomendado)
- Sistema Linux, macOS o Windows con WSL2

### Pasos para levantar el stack

```bash
# 1. Ir al directorio de Wazuh (single-node)
cd infra/wazuh

# 2. Aumentar vm.max_map_count (obligatorio en Linux)
sudo sysctl -w vm.max_map_count=262144

# 3. Generar los certificados TLS (solo la primera vez)
docker compose -f generate-indexer-certs.yml run --rm generator

# 4. Levantar el stack en segundo plano
docker compose up -d
```

### Acceso

| Servicio | URL / Puerto | Credenciales por defecto |
| :-- | :-- | :-- |
| Wazuh Dashboard | `https://localhost` | Configuradas en el stack (revisar `docker-compose.yml` / `config/`) |
| Wazuh API | `https://localhost:55000` | Coinciden con las variables `WAZUH_API_*` |
| Wazuh Indexer (OpenSearch) | `https://localhost:9200` | Coinciden con las variables `WAZUH_INDEXER_*` |

> **Nota:** El stack utiliza certificados auto-firmados. Por ese motivo es importante mantener `WAZUH_VERIFY_SSL=false` en el `.env` de Capazeta para pruebas locales. 

Para detener el entorno: `docker compose down`. Para detenerlo y eliminar volúmenes (borrando datos): `docker compose down -v`.

---

## ▶️ Uso

Para iniciar el asistente interactivo Capazeta desde la terminal:

```bash
uv run capazeta
```

O alternativamente ejecutando el módulo principal:

```bash
uv run python -m capazeta.main
```

Para actualizar o reconstruir el índice RAG de MITRE ATT&CK:

```bash
uv run python -m capazeta.rag.build --force
```

---

## 🗺️ Roadmap

### Para próximas iteraciones (Entrega Final)
- [ ] **Evaluación cuantitativa de Retrieval:** Implementación de métricas *Hit Rate@K*, *Mean Reciprocal Rank (MRR)* y *Recall@K* sobre un dataset de pruebas con logs/alertas de Wazuh mapeados a técnicas MITRE ATT&CK.
- [ ] **Evaluación de generación LLM:** Medición de *Fidelidad (Faithfulness)* y *Relevancia de la Respuesta (Answer Relevance)* utilizando [Ragas](https://docs.ragas.io/) integrado con [LangSmith](https://www.langchain.com/langsmith).
- [ ] **Baseline comparativo:** Comparación entre el sistema Capazeta, búsqueda manual por analista SOC y búsqueda tradicional por palabras clave (keyword/BM25) sobre el catálogo MITRE ATT&CK.
- [ ] **Contrastación con otras verticales de ciberseguridad:** Integración y mapeo a marcos complementarios como **MITRE D3FEND** (contramedidas defensivas), **ATT&CK for Cloud**, **ATT&CK for Mobile** y **ATT&CK for ICS**, permitiendo contrastar hallazgos entre diferentes dominios y enriquecer el razonamiento del agente.
- [ ] **Exportación de reportes a PDF:** Crear una herramienta `export_report_pdf` (análoga a la existente `report.py` para Markdown) que permita generar reportes profesionales en PDF con hallazgos, técnicas MITRE, artefactos e indicadores.
- [ ] **Persistencia de conversaciones:** Incorporación de persistencia de hilos con base de datos (PostgreSQL / SQLite Checkpointer).
- [ ] **Ampliación de herramientas:** Desarrollo de herramientas activas para los agentes `web_apis`, `mobile` y `ot_ics`.
- [ ] **Interfaz amigable** En lugar de seguir utilizando la terminal como interaccion migrarlo a la web o a una interfaz mas amigable para el usuario, por ejemplo con herramientas como Streamlit, Chainlit o Gradio.

---

## 👥 Autor

- **Joaquin Cernik** — [GitHub](https://github.com/joaquincernik) · [LinkedIn](https://linkedin.com/in/joaquincernik)

---

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](LICENSE) — ver el archivo `LICENSE` para más detalle.

---

## 🙏 Agradecimientos y referencias

- Frameworks **LangChain** y **LangGraph** por la infraestructura de orquestación multi-agente.
- **MITRE ATT&CK®** por la matriz pública de conocimiento de técnicas y tácticas de ciberseguridad.
- Proyecto **Wazuh** por la plataforma Open Source de SIEM y XDR.
