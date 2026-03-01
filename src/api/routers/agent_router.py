from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.agents.graph import app as agent_app

router = APIRouter(prefix="/agent", tags=["Agent"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    credit_profile: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    risk_decision: Optional[str] = None
    risk_reasoning: Optional[str] = None
    advice: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the Journey Coach agent.
    """
    # Convert history to LangChain messages if needed
    # For now, we rely on the graph state persistence or just pass the current message
    # In a real app, we would load history from a store based on session_id.
    
    # Simple stateless invocation for Phase 2 POC
    # Pass history if provided
    messages = []
    for msg in request.history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
            
    messages.append(HumanMessage(content=request.message))
    
    inputs = {"messages": messages}
    
    try:
        result = await agent_app.ainvoke(inputs)
        
        last_message = result["messages"][-1]
        response_text = last_message.content
        
        profile = result.get("credit_profile")
        profile_dict = profile.model_dump() if profile else None
        
        return ChatResponse(
            response=response_text,
            credit_profile=profile_dict,
            risk_score=result.get("risk_score"),
            risk_decision=result.get("risk_decision"),
            risk_reasoning=result.get("risk_reasoning"),
            advice=result.get("advice")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
