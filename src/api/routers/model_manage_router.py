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
            return {"status": "reloaded", "message": "Model reloaded successfully from MLflow"}
        else:
            log_audit("model_reload", "/model/reload", "failed")
            raise HTTPException(status_code=500, detail="Failed to reload model")
    except Exception as e:
        logger.error(f"Failed to reload model: {e}")
        log_audit("model_reload", "/model/reload", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_model_status() -> Dict[str, Any]:
    model = CreditRiskModel()._model
    return {
        "loaded": model is not None,
        "type": str(type(model)) if model else None
    }
