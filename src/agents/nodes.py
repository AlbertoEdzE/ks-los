import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.prebuilt import ToolNode

from src.config.llm import get_llm
from src.agents.state import AgentState
from src.agents.prompts import (
    JOURNEY_COACH_SYSTEM_PROMPT, 
    ADVISORY_SYSTEM_PROMPT, 
    RISK_ENGINE_SYSTEM_PROMPT,
    build_risk_engine_user_prompt
)
from src.agents.tools import GenerateProfileTool
from src.shared.types import ApplicantCreditProfile
from src.core.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

# Initialize LLM and Tools
llm = get_llm()
tools = [GenerateProfileTool()]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

# Lazy initialization of KB to avoid import-time DB connection issues
kb = None

def get_kb():
    global kb
    if kb is None:
        try:
            kb = KnowledgeBase()
        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeBase: {e}")
            return None
    return kb

def journey_coach_node(state: AgentState):
    """
    Interacts with the user to gather information.
    """
    messages = state["messages"]
    
    # Prepend system prompt if not present
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=JOURNEY_COACH_SYSTEM_PROMPT)] + messages
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def risk_engine_node(state: AgentState):
    """
    Analyzes the credit profile using RAG-based policy lookup.
    """
    profile = state.get("credit_profile")
    if not profile:
        return {"risk_score": None}
    
    # 1. Retrieve Policy Context
    kb_instance = get_kb()
    policy_context = ""
    if kb_instance:
        try:
            # Query based on key profile attributes
            queries = [
                f"Credit policy for {profile.identity.address.territory}",
                f"Minimum credit score for {profile.summary.score_band}",
                "Thin file policy" if profile.summary.thin_file else "Standard approval criteria",
                "DTI limits"
            ]
            
            docs = []
            for q in queries:
                docs.extend(kb_instance.query(q, k=2))
            
            # Deduplicate and format
            seen_content = set()
            unique_docs = []
            for d in docs:
                if d.page_content not in seen_content:
                    seen_content.add(d.page_content)
                    unique_docs.append(d)
            
            policy_context = "\n\n".join([d.page_content for d in unique_docs])
        except Exception as e:
            logger.error(f"RAG Retrieval failed: {e}")
            policy_context = "Policy retrieval unavailable. Use standard conservative fallback."
    
    # 2. Construct Analysis Prompt
    user_prompt = build_risk_engine_user_prompt(policy_context, profile)
    
    # 3. LLM Evaluation
    try:
        response = llm.invoke([
            SystemMessage(content=RISK_ENGINE_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ])
        
        content = response.content
        # Basic JSON parsing cleanup
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        result = json.loads(content.strip())
        
        return {
            "risk_decision": result.get("decision", "MANUAL_REVIEW"),
            "risk_score": float(result.get("risk_score", 0.0)),
            "risk_reasoning": result.get("reasoning", "Analysis failed.")
        }
        
    except Exception as e:
        logger.error(f"Risk Engine Analysis failed: {e}")
        # Fallback to rule-based stub
        base_score = profile.summary.credit_score
        risk_score = max(0, min(100, (base_score - 300) / 5.5))
        return {
            "risk_decision": "MANUAL_REVIEW",
            "risk_score": risk_score,
            "risk_reasoning": "Automated analysis failed. Manual review required."
        }

def advisory_node(state: AgentState):
    """
    Generates advice based on the profile and risk score.
    """
    profile = state.get("credit_profile")
    risk_score = state.get("risk_score")
    decision = state.get("risk_decision")
    reasoning = state.get("risk_reasoning")
    
    if not profile:
        return {"advice": "Unable to generate advice without a profile."}
        
    prompt = f"""
    Applicant: {profile.identity.full_name}
    Territory: {profile.identity.address.territory}
    Credit Score: {profile.summary.credit_score} ({profile.summary.score_band})
    
    Risk Decision: {decision}
    Risk Score: {risk_score}
    Reasoning: {reasoning}
    
    Please provide your advisory recommendation to the client, explaining the decision and next steps.
    """
    
    messages = [
        SystemMessage(content=ADVISORY_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    # Wrap advice in AIMessage so it appears in chat history
    advice_message = AIMessage(content=f"**Advisory Recommendation:**\n\n**Decision: {decision}**\n\n{response.content}")
    
    return {"advice": response.content, "messages": [advice_message]}

def profile_parser_node(state: AgentState):
    """
    Parses the tool output to update the credit_profile in state.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if isinstance(last_message, ToolMessage):
        try:
            profile_json = last_message.content
            profile = ApplicantCreditProfile.model_validate_json(profile_json)
            return {"credit_profile": profile}
        except Exception as e:
            # If parsing fails, just return nothing, maybe log error
            return {}
            
    return {}
