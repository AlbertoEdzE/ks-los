from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from src.shared.auth import require_role
from src.ml.inference import CreditRiskModel
from src.shared.types import ApplicantCreditProfile

router = APIRouter(prefix="/explain", tags=["explain"])

class ExplainRequest(BaseModel):
  profile: ApplicantCreditProfile

@router.post("/inference")
def explain_inference(req: ExplainRequest, _: bool = Depends(require_role("viewer"))) -> Dict[str, Any]:
  try:
    model = CreditRiskModel()
    # feature values aligned with inference
    p = req.profile
    feature_values = {
      "age": 2024 - p.identity.date_of_birth.year,
      "credit_score": p.summary.credit_score,
      "utilization_ratio": p.summary.utilization_ratio,
      "total_debt": p.summary.total_current_balance_xcd,
      "history_length_months": p.summary.months_oldest_account,
      "derogatory_marks": p.summary.derogatory_marks,
      "thin_file_flag": 1 if p.summary.thin_file else 0
    }
    importances = {}
    try:
      fi = getattr(model._model, "feature_importances_", None)
      cols = getattr(model._model, "feature_names_in_", None)
      if fi is not None and cols is not None:
        importances = {str(cols[i]): float(fi[i]) for i in range(len(fi))}
    except Exception:
      importances = {}
    score = model.predict(req.profile)["score"]
    return {"score": score, "feature_values": feature_values, "feature_importances": importances}
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Explain failed: {e}")
