import os
from dotenv import load_dotenv

load_dotenv()

# Ajusta el nombre del modelo según tu disponibilidad en la API
DEFAULT_MODEL_NAME = "google_genai:gemini-2.5-flash-lite"
MODEL_NAME = (os.getenv("MODEL_NAME") or "").strip() or DEFAULT_MODEL_NAME
THREAD_ID = os.getenv("THREAD_ID", "capazeta_thread")

# Wazuh
WAZUH_API_URL = os.getenv("WAZUH_API_URL", "https://localhost:55000").strip().rstrip("/")
WAZUH_API_USER = os.getenv("WAZUH_API_USER", "wazuh").strip()
WAZUH_API_PASSWORD = (os.getenv("WAZUH_API_PASSWORD") or "").strip()
WAZUH_INDEXER_URL = os.getenv("WAZUH_INDEXER_URL", "https://localhost:9200").strip().rstrip("/")
WAZUH_INDEXER_USER = os.getenv("WAZUH_INDEXER_USER", "admin").strip()
WAZUH_INDEXER_PASSWORD = (os.getenv("WAZUH_INDEXER_PASSWORD") or "").strip()
WAZUH_VERIFY_SSL = (os.getenv("WAZUH_VERIFY_SSL", "false") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "si",
    "sí",
)

# RAG MITRE ATT&CK
EMBEDDING_MODEL = (
    os.getenv("EMBEDDING_MODEL") or "models/gemini-embedding-001"
).strip()
MITRE_STIX_URL = (
    os.getenv("MITRE_STIX_URL")
    or "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "enterprise-attack/enterprise-attack.json"
).strip()
MITRE_DATA_DIR = (os.getenv("MITRE_DATA_DIR") or "data/mitre").strip()
