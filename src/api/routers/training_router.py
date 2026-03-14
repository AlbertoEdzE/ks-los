from fastapi import APIRouter, HTTPException, Response, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
import os
from src.agents.training_agent import propose_training_plan, execute_training
from src.ml.drift import run_drift_check
from src.ml.training_manager import training_manager
from src.ml.inference import CreditRiskModel
from src.shared.metrics import request_counter, training_runs_total, drift_runs_total
from src.shared.auth import require_role
from src.shared.audit import log_audit

router = APIRouter(prefix="/training", tags=["training"])
logger = logging.getLogger(__name__)

class TrainingContext(BaseModel):
    rationale: str = "Periodic refresh to improve AUC and stability"
    n_samples: int = 1000
    noise_level: float = 0.1

class TrainingPlan(BaseModel):
    hyperparameters: Dict[str, Any]
    n_samples: int
    notes: str

class BatchTestRequest(BaseModel):
    samples: List[Dict[str, Any]]

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
def run_training(plan: TrainingPlan, background_tasks: BackgroundTasks, _: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        request_counter.labels(endpoint="/training/execute").inc()
        training_runs_total.inc()
        
        if training_manager.is_training:
            raise HTTPException(status_code=409, detail="Training already in progress")

        if os.getenv("PYTEST_CURRENT_TEST"):
            result = execute_training(plan.model_dump())
            log_audit("training_execute", "/training/execute", "success", {"n_samples": plan.n_samples})
            return {"status": "completed", "message": "Training completed", "result": result}

        background_tasks.add_task(execute_training, plan.model_dump())

        log_audit("training_execute", "/training/execute", "success", {"n_samples": plan.n_samples})
        return {"status": "started", "message": "Training started in background"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute training: {e}")
        log_audit("training_execute", "/training/execute", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Training failed")

@router.get("/status")
def get_status(_: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    return training_manager.get_status()

@router.post("/test")
def batch_test(req: BatchTestRequest, _: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        model = CreditRiskModel()
        results = []
        for sample in req.samples:
            res = model.predict(sample)
            prob = res["probability_good"]
            
            # Risk Level Logic: Low prob of being good = High Risk
            if prob < 0.4:
                risk_level = "High"
            elif prob > 0.7:
                risk_level = "Low"
            else:
                risk_level = "Medium"
                
            results.append({
                "input": sample,
                "prediction": 1 if prob > 0.5 else 0,
                "probability": prob,
                "risk_level": risk_level
            })

        return {"results": results}
    except Exception as e:
        logger.error(f"Batch test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/drift")
def run_drift(_: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        request_counter.labels(endpoint="/training/drift").inc()
        drift_runs_total.inc()
        path = run_drift_check()
        log_audit("drift_run", "/training/drift", "success")
        return {"message": "Drift check completed", "report_path": path, "report_endpoint": "/training/drift/report"}
    except Exception as e:
        logger.error(f"Drift check failed: {e}")
        log_audit("drift_run", "/training/drift", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
def get_current_model_metrics(_: bool = Depends(require_role("viewer"))) -> Dict[str, Any]:
    """
    Returns metrics for the currently loaded model.
    Since we don't store live metrics in memory persistently across restarts (unless using a DB),
    we can return the metadata of the currently loaded model version.
    """
    try:
        model = CreditRiskModel()
        version = model.get_version()
        if not version:
            return {"status": "no_model_loaded"}
            
        # Retrieve run info for this version to get metrics logged during training
        import mlflow
        from src.ml.ml_config import MLFLOW_TRACKING_URI, REGISTERED_MODEL_NAME
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()
        
        versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
        target = next((v for v in versions if v.version == version), None)
        
        if not target:
             return {"status": "version_not_found", "version": version}

        run = client.get_run(target.run_id)
        metrics = run.data.metrics
        
        return {
            "version": version,
            "stage": target.current_stage,
            "run_id": target.run_id,
            "creation_timestamp": target.creation_timestamp,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to get model metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
