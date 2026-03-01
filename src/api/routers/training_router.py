from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Dict, Any
import logging
from src.agents.training_agent import propose_training_plan, execute_training
from src.ml.drift import run_drift_check

router = APIRouter(prefix="/training", tags=["training"])
logger = logging.getLogger(__name__)

class TrainingContext(BaseModel):
    rationale: str = "Periodic refresh to improve AUC and stability"

class TrainingPlan(BaseModel):
    hyperparameters: Dict[str, Any]
    n_samples: int
    notes: str

@router.post("/plan")
def generate_plan(ctx: TrainingContext) -> Dict[str, Any]:
    try:
        plan = propose_training_plan(context=ctx.model_dump())
        return {"plan": plan}
    except Exception as e:
        logger.error(f"Failed to generate training plan: {e}")
        raise HTTPException(status_code=500, detail="Plan generation failed")

@router.post("/execute")
def run_training(plan: TrainingPlan) -> Dict[str, Any]:
    try:
        result = execute_training(plan.model_dump())
        return {"result": result}
    except Exception as e:
        logger.error(f"Failed to execute training: {e}")
        raise HTTPException(status_code=500, detail="Training failed")

@router.post("/drift")
def run_drift() -> Dict[str, Any]:
    try:
        path = run_drift_check()
        return {"report_path": path, "report_endpoint": "/training/drift/report"}
    except Exception as e:
        logger.error(f"Failed to run drift: {e}")
        raise HTTPException(status_code=500, detail="Drift run failed")

@router.get("/drift/report")
def get_drift_report() -> Response:
    try:
        path = "doc/04_documentation/phase_4/drift_report.html"
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        return Response(content=html, media_type="text/html")
    except Exception as e:
        logger.error(f"Failed to read drift report: {e}")
        raise HTTPException(status_code=404, detail="Report not found")
