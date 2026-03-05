from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from src.ml.inference import CreditRiskModel
from src.shared.auth import require_role
from src.shared.audit import log_audit

router = APIRouter(prefix="/model", tags=["model"])
logger = logging.getLogger(__name__)

@router.post("/reload")
def reload_model(_: bool = Depends(require_role("admin"))) -> Dict[str, Any]:
    try:
        success = CreditRiskModel().reload_model()
        if success:
            log_audit("model_reload", "/model/reload", "success")
            return {"status": "reloaded", "message": "Model reloaded successfully from MLflow", "version": CreditRiskModel().get_version()}
        else:
            log_audit("model_reload", "/model/reload", "failed")
            raise HTTPException(status_code=500, detail="Failed to reload model")
    except Exception as e:
        logger.error(f"Failed to reload model: {e}")
        log_audit("model_reload", "/model/reload", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rollback")
def rollback_model(_: bool = Depends(require_role("admin"))) -> Dict[str, Any]:
    try:
        success, message = CreditRiskModel().rollback()
        if success:
            log_audit("model_rollback", "/model/rollback", "success", {"message": message})
            return {"status": "rolled_back", "message": message, "version": CreditRiskModel().get_version()}
        else:
            log_audit("model_rollback", "/model/rollback", "failed", {"reason": message})
            raise HTTPException(status_code=400, detail=f"Rollback failed: {message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback model: {e}")
        log_audit("model_rollback", "/model/rollback", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/versions")
def list_versions(_: bool = Depends(require_role("operator"))) -> Dict[str, Any]:
    try:
        versions = CreditRiskModel().list_versions()
        return {"versions": versions}
    except Exception as e:
        logger.error(f"Failed to list versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_model_status() -> Dict[str, Any]:
    model_instance = CreditRiskModel()
    model = model_instance._model
    return {
        "loaded": model is not None,
        "type": str(type(model)) if model else None,
        "version": model_instance.get_version()
    }
