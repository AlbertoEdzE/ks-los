from langchain_ollama import ChatOllama
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from langchain_core.messages import AIMessage
import os
import re

# Default to Qwen 2.5 7B as per architecture
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

class _TestLLM:
    def __init__(self, tools=None, temperature: float = 0.7):
        self._tools = tools or []
        self._temperature = temperature

    def bind_tools(self, tools):
        return _TestLLM(tools=tools, temperature=self._temperature)

    def invoke(self, messages):
        system_content = ""
        for m in messages:
            if m.__class__.__name__ == "SystemMessage":
                system_content = m.content or ""
                break

        last_user = ""
        for m in reversed(messages):
            if m.__class__.__name__ == "HumanMessage":
                last_user = m.content or ""
                break

        if "Credit Risk Officer" in system_content or '"risk_score"' in system_content:
            return AIMessage(content='{"decision":"MANUAL_REVIEW","risk_score":50,"reasoning":"Test mode response."}')

        if "Expert Financial Advisor" in system_content:
            return AIMessage(content="Test mode advisory response.")

        age = None
        territory = None
        m_age = re.search(r"(\d{2})\s*year", last_user, flags=re.IGNORECASE)
        if m_age:
            try:
                age = int(m_age.group(1))
            except Exception:
                age = None

        m_terr = re.search(r"\(([A-Z]{2})\)", last_user)
        if m_terr:
            territory = m_terr.group(1)

        if age is not None and territory is not None:
            tool_calls = [
                {
                    "id": "call_generate_profile",
                    "type": "tool_call",
                    "name": "generate_credit_profile",
                    "args": {"age": age, "territory": territory},
                }
            ]
            return AIMessage(content="", additional_kwargs={"tool_calls": tool_calls}, tool_calls=tool_calls)

        return AIMessage(content="Journey Coach (test mode).")


def get_llm(temperature: float = 0.7):
    """
    Returns a configured ChatOllama instance.
    """
    if os.getenv("PYTEST_CURRENT_TEST"):
        return _TestLLM(temperature=temperature)
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=MODEL_NAME,
        temperature=temperature,
        callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
        keep_alive="5m"
    )
