from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from src.shared.types import ApplicantCreditProfile

class AgentState(TypedDict):
    """
    The state of the agent workflow.
    """
    messages: Annotated[List[Any], add_messages]
    applicant_id: Optional[str]
    credit_profile: Optional[ApplicantCreditProfile]
    
    # Risk Engine Outputs
    risk_score: Optional[float]
    risk_decision: Optional[str] # APPROVED, DECLINED, MANUAL_REVIEW
    risk_reasoning: Optional[str]
    
    advice: Optional[str]
    next_step: Optional[str]
    
    # Context data
    user_input: Optional[str]
    session_id: Optional[str]
