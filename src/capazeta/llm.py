from langchain.chat_models import init_chat_model
from capazeta.config import MODEL_NAME

def get_llm():
    return init_chat_model(MODEL_NAME)