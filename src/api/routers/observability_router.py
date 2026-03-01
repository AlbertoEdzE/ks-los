from fastapi import APIRouter
from typing import Dict, Any
import os
from src.shared.metrics import training_runs_total, drift_runs_total, risk_inference_total

router = APIRouter(prefix="/observability", tags=["observability"])

@router.get("/summary")
def summary() -> Dict[str, Any]:
    return {
        "training_runs": training_runs_total._value.get(),
        "drift_runs": drift_runs_total._value.get(),
        "risk_inferences": risk_inference_total._value.get(),
        "mlflow_url": os.getenv("MLFLOW_URL", "http://localhost:5000"),
        "drift_report_endpoint": "/training/drift/report"
    }
