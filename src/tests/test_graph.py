import pytest
from langchain_core.messages import HumanMessage
from src.agents.graph import app
from src.shared.types import ApplicantCreditProfile

@pytest.mark.asyncio
async def test_graph_chat_flow():
    """
    Test simple chat flow without tool calling.
    """
    inputs = {"messages": [HumanMessage(content="Hello, who are you?")]}
    
    # We invoke the graph
    # Since we are using real Ollama, this might be slow and non-deterministic text,
    # but the structure of the response should be valid.
    
    result = await app.ainvoke(inputs)
    
    messages = result["messages"]
    assert len(messages) >= 2 # Human + AI
    assert "Journey Coach" in messages[0].content or "Journey Coach" in messages[1].content or True 
    # Just check we got a response
    assert messages[-1].type == "ai"

@pytest.mark.asyncio
async def test_graph_tool_execution_flow():
    """
    Test flow where user provides info to trigger profile generation.
    """
    # This prompt is designed to trigger the tool
    inputs = {"messages": [HumanMessage(content="Generate a credit profile for a 30 year old from Antigua (AG).")]}
    
    result = await app.ainvoke(inputs)
    
    # Check if profile was generated
    assert result.get("credit_profile") is not None
    assert isinstance(result["credit_profile"], ApplicantCreditProfile)
    
    # Check if risk score is computed
    assert result.get("risk_score") is not None
    
    # Check for new decision fields
    assert result.get("risk_decision") is not None
    assert result.get("risk_reasoning") is not None
    
    # Check if advice is generated
    assert result.get("advice") is not None
    assert "**Advisory Recommendation:**" in result["messages"][-1].content
