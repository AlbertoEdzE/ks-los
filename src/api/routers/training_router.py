from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel
from typing import Dict, Any
import logging
from src.agents.training_agent import propose_training_plan, execute_training
from src.ml.drift import run_drift_check
from src.shared.metrics import request_counter, training_runs_total, drift_runs_total
from src.shared.auth import require_role
from src.shared.audit import log_audit

router = APIRouter(prefix="/training", tags=["training"])
logger = logging.getLogger(__name__)

class TrainingContext(BaseModel):
    rationale: str = "Periodic refresh to improve AUC and stability"

class TrainingPlan(BaseModel):
    hyperparameters: Dict[str, Any]
    n_samples: int
    notes: str

@router.post("/plan")
def generate_plan(ctx: TrainingContext, _: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        request_counter.labels(endpoint="/training/plan").inc()
        plan = propose_training_plan(context=ctx.model_dump())
        log_audit("training_plan", "/training/plan", "success", {"rationale": ctx.rationale})
        return {"plan": plan}
    except Exception as e:
        logger.error(f"Failed to generate training plan: {e}")
        log_audit("training_plan", "/training/plan", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Plan generation failed")

@router.post("/execute")
def run_training(plan: TrainingPlan, _: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        request_counter.labels(endpoint="/training/execute").inc()
        training_runs_total.inc()
        result = execute_training(plan.model_dump())
        log_audit("training_execute", "/training/execute", "success", {"n_samples": plan.n_samples})
        return {"result": result}
    except Exception as e:
        logger.error(f"Failed to execute training: {e}")
        log_audit("training_execute", "/training/execute", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Training failed")

@router.post("/drift")
def run_drift(_: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        request_counter.labels(endpoint="/training/drift").inc()
        drift_runs_total.inc()
        path = run_drift_check()
        log_audit("drift_run", "/training/drift", "success")
        return {"report_path": path, "report_endpoint": "/training/drift/report"}
    except Exception as e:
        logger.error(f"Failed to run drift: {e}")
        log_audit("drift_run", "/training/drift", "error", {"error": str(e)})
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
