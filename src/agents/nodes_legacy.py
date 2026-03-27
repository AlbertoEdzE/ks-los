import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from src.config.llm import get_llm
from src.agents.state import AgentState
from src.agents.prompts import (
    JOURNEY_COACH_SYSTEM_PROMPT, 
    ADVISORY_SYSTEM_PROMPT, 
    RISK_ENGINE_SYSTEM_PROMPT,
    build_risk_engine_user_prompt
)
from src.agents.tools import GenerateProfileTool  # This now works via importlib in __init__.py
from src.shared.types import ApplicantCreditProfile
from src.core.knowledge_base import KnowledgeBase
from src.ml.inference import CreditRiskModel
try:
    import mlflow
except Exception:
    mlflow = None
import os
from src.ml.ml_config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME
import time
from src.shared.metrics import risk_inference_total, inference_latency_seconds
from opentelemetry import trace
from src.shared.correlation import get_correlation_id

logger = logging.getLogger(__name__)

llm = None
tools = [GenerateProfileTool()]
# tool_node = ToolNode(tools)  # DISABLED

# Lazy initialization of KB to avoid import-time DB connection issues
kb = None
ml_model = None

def _get_runtime_llm():
    global llm
    if llm is None:
        llm = get_llm()
    return llm

def _get_runtime_llm_with_tools():
    base = _get_runtime_llm()
    return base.bind_tools(tools)

def get_kb():
    global kb
    if kb is None:
        try:
            kb = KnowledgeBase()
        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeBase: {e}")
            return None
    return kb

def get_ml_model():
    global ml_model
    if ml_model is None:
        try:
            ml_model = CreditRiskModel()
        except Exception as e:
            logger.error(f"Failed to initialize ML Model: {e}")
            return None
    return ml_model

def journey_coach_node(state: AgentState):
    """
    Interacts with the user to gather information.
    """
    messages = state["messages"]
    
    # Prepend system prompt if not present
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=JOURNEY_COACH_SYSTEM_PROMPT)] + messages
    
    llm_with_tools = _get_runtime_llm_with_tools()
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    tool_calls = []
    if getattr(last_message, "tool_calls", None):
        tool_calls = list(last_message.tool_calls)
    else:
        additional = getattr(last_message, "additional_kwargs", None) or {}
        if isinstance(additional, dict) and additional.get("tool_calls"):
            tool_calls = list(additional["tool_calls"])

    if not tool_calls:
        user_text = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_text = m.content or ""
                break
        text = user_text.lower()
        if "credit profile" in text or "generate a credit profile" in text:
            import re

            age = None
            territory = None

            m_age = re.search(r"\b(\d{2})\b", user_text)
            if m_age:
                try:
                    age = int(m_age.group(1))
                except Exception:
                    age = None

            m_territory = re.search(r"\(([A-Za-z]{2,3})\)", user_text)
            if m_territory:
                territory = m_territory.group(1).upper()
            else:
                m_territory2 = re.search(r"\bfrom\s+([A-Za-z]{2,3})\b", user_text, re.IGNORECASE)
                if m_territory2:
                    territory = m_territory2.group(1).upper()

            if age is not None and territory:
                tool_calls = [{"id": "heuristic_generate_credit_profile", "name": "generate_credit_profile", "args": {"age": age, "territory": territory}}]

    if not tool_calls:
        return {}

    tools_by_name = {t.name: t for t in tools}
    tool_messages: list[ToolMessage] = []

    for call in tool_calls:
        call_id = None
        name = None
        args = None

        if isinstance(call, dict):
            call_id = call.get("id")
            name = call.get("name") or call.get("function", {}).get("name")
            args = call.get("args") or call.get("function", {}).get("arguments")
        else:
            call_id = getattr(call, "id", None)
            name = getattr(call, "name", None)
            args = getattr(call, "args", None)

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if args is None:
            args = {}

        tool = tools_by_name.get(name)
        if not tool:
            tool_messages.append(
                ToolMessage(
                    content=json.dumps({"error": f"Unknown tool: {name}"}),
                    tool_call_id=call_id or "unknown",
                )
            )
            continue

        try:
            result = tool._run(**args)
        except Exception as e:
            result = json.dumps({"error": str(e)})

        tool_messages.append(
            ToolMessage(
                content=result,
                tool_call_id=call_id or name or "tool_call",
            )
        )

    return {"messages": tool_messages}

def risk_engine_node(state: AgentState):
    """
    Analyzes the credit profile using:
    1. Deterministic metrics from calculation engines (Task 1)
    2. RAG-based policy lookup
    3. XGBoost Predictive Model
    
    The LLM synthesizes all three sources for a grounded decision.
    """
    profile = state.get("credit_profile")
    if not profile:
        return {"risk_score": None}

    # 0. Get Deterministic Metrics from Calculation Engines (NEW - Task 3)
    calculated_metrics = state.get("calculated_metrics")
    metrics_context = ""
    if calculated_metrics:
        metrics_context = f"""
--- DETERMINISTIC CALCULATIONS (Task 1 Engines) ---
EMI: {calculated_metrics.get('emi', 'N/A')}
FOIR: {calculated_metrics.get('foir', 'N/A'):.2f}%
DTI: {calculated_metrics.get('dti', 'N/A'):.2f}
Approval Probability: {calculated_metrics.get('approval_probability', 'N/A')}%
Risk Grade: {calculated_metrics.get('risk_grade', 'N/A')}
APR: {calculated_metrics.get('apr', 'N/A'):.2f}%
STP Tier: {calculated_metrics.get('stp_tier', 'N/A')}
"""
        logger.info(f"[RiskEngine] Using calculated metrics: FOIR={calculated_metrics.get('foir')}, Approval Prob={calculated_metrics.get('approval_probability')}%")
    else:
        metrics_context = "\n--- DETERMINISTIC CALCULATIONS ---\nNot available. Use standard assessment.\n"
        logger.warning("[RiskEngine] No calculated metrics available")

    # 1. Retrieve Policy Context (RAG)
    kb_instance = get_kb()
    policy_context = ""
    if kb_instance:
        try:
            queries = [
                f"Credit policy for {profile.identity.address.territory}",
                f"Minimum credit score for {profile.summary.score_band}",
                "Thin file policy" if profile.summary.thin_file else "Standard approval criteria",
                "DTI limits"
            ]

            docs = []
            for q in queries:
                docs.extend(kb_instance.query(q, k=2))

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

    # 2. Get ML Prediction (XGBoost)
    ml_instance = get_ml_model()
    ml_score = 0.5
    ml_prob = 0.5
    if ml_instance:
        ml_result = ml_instance.predict(profile)
        ml_prob = ml_result["probability_good"]
        ml_score = ml_result["score"] * 100 # Convert to 0-100 scale for consistency
        logger.info(f"ML Model Prediction: Prob={ml_prob:.4f}, Score={ml_score:.2f}")

    # 3. Construct Analysis Prompt (Ensemble Context)
    # We inject the ML score AND calculated metrics into the prompt
    user_prompt = build_risk_engine_user_prompt(
        {
            "policy_context": policy_context,
            "profile": profile.model_dump() if hasattr(profile, "model_dump") else str(profile),
        }
    )
    user_prompt += f"\n\n{metrics_context}"
    user_prompt += f"\n\n--- PREDICTIVE MODEL ---"
    user_prompt += f"\nXGBoost Risk Score: {ml_score:.1f}/100"
    user_prompt += f"\nProbability of Good Credit: {ml_prob:.2%}"
    user_prompt += f"\nNote: Low scores (<50) indicate high risk of default based on historical data."
    
    # 4. LLM Evaluation
    tracer = trace.get_tracer("risk_engine")
    start = time.monotonic()
    try:
        with tracer.start_as_current_span("risk_inference") as span:
            runtime_llm = _get_runtime_llm()
            response = runtime_llm.invoke([
            SystemMessage(content=RISK_ENGINE_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ])
        
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        result = json.loads(content.strip())
        
        # Ensemble Override Logic (Optional Rule Layer)
        decision = result.get("decision", "MANUAL_REVIEW")
        reasoning = result.get("reasoning", "Analysis failed.")
        try:
            span.set_attribute("risk.decision", decision)
            span.set_attribute("risk.ml_prob_good", float(ml_prob))
            span.set_attribute("risk.ml_score", float(ml_score))
        except Exception:
            pass
        
        # Safety Guardrail: If ML is extremely confident of default, force Manual Review even if Policy Passes
        if decision == "APPROVED" and ml_prob < 0.2:
            decision = "MANUAL_REVIEW"
            reasoning += f" [SYSTEM OVERRIDE] Downgraded to Manual Review due to high ML predicted default risk ({ml_prob:.1%})."
        
        result_obj = {
            "risk_decision": decision,
            "risk_score": float(result.get("risk_score", ml_score)),
            "risk_reasoning": reasoning
        }
        
        # Inference logging to MLflow and file
        if mlflow is not None:
            try:
                mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
                mlflow.set_experiment(EXPERIMENT_NAME)
                with mlflow.start_run(run_name="inference", nested=True):
                    cid = get_correlation_id()
                    mlflow.log_params({
                        "age": profile.identity.age if hasattr(profile.identity, "age") else None,
                        "credit_score": profile.summary.credit_score,
                        "utilization_ratio": profile.summary.utilization_ratio,
                        "total_debt": profile.summary.total_current_balance_xcd,
                        "history_length_months": profile.summary.months_oldest_account,
                        "derogatory_marks": profile.summary.derogatory_marks,
                        "thin_file_flag": 1 if profile.summary.thin_file else 0
                    })
                    mlflow.log_metrics({
                        "ml_prob_good": ml_prob,
                        "ml_score": ml_score,
                        "risk_score": result_obj["risk_score"]
                    })
                    tags = {"decision": decision}
                    if cid:
                        tags["correlation_id"] = cid
                    mlflow.set_tags(tags)
            except Exception as e:
                logger.error(f"MLflow inference logging failed: {e}")
        
        # Append to local inference log CSV
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/inference_log.csv", "a", encoding="utf-8") as f:
                f.write(",".join([
                    str(profile.summary.credit_score),
                    str(profile.summary.utilization_ratio),
                    str(profile.summary.total_current_balance_xcd),
                    str(profile.summary.months_oldest_account),
                    str(profile.summary.derogatory_marks),
                    str(1 if profile.summary.thin_file else 0),
                    f"{ml_prob:.6f}",
                    f"{ml_score:.2f}",
                    decision
                ]) + "\n")
        except Exception as e:
            logger.error(f"Local inference logging failed: {e}")
        
        duration = time.monotonic() - start
        risk_inference_total.inc()
        inference_latency_seconds.observe(duration)
        return result_obj
        
    except Exception as e:
        logger.error(f"Risk Engine Analysis failed: {e}")
        # Fallback
        return {
            "risk_decision": "MANUAL_REVIEW",
            "risk_score": ml_score,
            "risk_reasoning": f"Automated analysis failed. Fallback to ML Score: {ml_score:.1f}"
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
    
    runtime_llm = _get_runtime_llm()
    response = runtime_llm.invoke(messages)
    
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
