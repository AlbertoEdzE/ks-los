from typing import Dict, Any
import logging
import mlflow
from src.config.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from src.ml.train import train_model
from src.ml.ml_config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a training orchestration assistant for a credit risk model. "
    "Propose a concise training plan using local data synthesis and XGBoost. "
    "Return strict JSON with keys: hyperparameters, n_samples, notes. "
    "Use safe defaults and keep it reproducible."
)

def propose_training_plan(context: Dict[str, Any]) -> Dict[str, Any]:
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context: {context}. Propose plan.")
    ]
    response = llm.invoke(messages)
    content = response.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    import json
    plan = json.loads(content)
    return plan

def execute_training(plan: Dict[str, Any]) -> Dict[str, Any]:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    hyperparams = plan.get("hyperparameters", {})
    n_samples = int(plan.get("n_samples", 2000))
    result = train_model(params=hyperparams, n_samples=n_samples)
    return result

