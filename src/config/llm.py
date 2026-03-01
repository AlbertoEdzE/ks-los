from langchain_ollama import ChatOllama
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
import os

# Default to Qwen 2.5 7B as per architecture
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def get_llm(temperature: float = 0.7):
    """
    Returns a configured ChatOllama instance.
    """
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=MODEL_NAME,
        temperature=temperature,
        callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
        keep_alive="5m"
    )
