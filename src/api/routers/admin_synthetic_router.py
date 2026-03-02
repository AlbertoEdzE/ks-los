from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
import threading
from datetime import date, timedelta
from src.agents.data_synthesizer.scdg import SCDG
from src.ml.inference import CreditRiskModel
from src.shared.types import ApplicantCreditProfile
from src.shared.audit import log_audit

router = APIRouter(prefix="/admin/synthetic", tags=["admin_synthetic"])

class GenerateRequest(BaseModel):
    count: int
    territory: str = "ECCU"
    archetype: Optional[str] = None
    seed: Optional[str] = None

_lock = threading.Lock()
_status: Dict[str, Any] = {"status": "idle", "progress": 0, "message": ""}
_dataset: List[Dict[str, Any]] = []

def _decide(profile: ApplicantCreditProfile) -> Dict[str, Any]:
    model = CreditRiskModel()
    pred = model.predict(profile)
    prob = pred["probability_good"]
    decision = "APPROVED" if prob >= 0.6 else "DECLINED"
    reasoning = f"Threshold decision based on probability_good={prob:.3f} (>=0.6 => APPROVED)"
    # Application record
    application_id = f"app_{hash(profile.identity.full_name) & 0xffff_ffff:x}"
    app = {
        "application_id": application_id,
        "applicant_name": profile.identity.full_name,
        "territory": profile.metadata.territory,
        "decision": decision,
        "probability_good": prob,
        "created_date": date.today().isoformat(),
    }
    # Repayments/events if approved
    events: List[Dict[str, Any]] = []
    repayments: List[Dict[str, Any]] = []
    if decision == "APPROVED":
        months = 12
        monthly = max(10.0, profile.summary.total_current_balance_xcd / max(1, months))
        for m in range(months):
            due_date = (date.today() + timedelta(days=30 * (m + 1))).isoformat()
            status = "ON_TIME"
            events.append({"type": "SCHEDULED_PAYMENT", "due_date": due_date, "amount_xcd": monthly, "status": status})
            repayments.append({"date": due_date, "amount_xcd": monthly, "status": status})
    return {"application": app, "events": events, "repayments": repayments, "reasoning": reasoning}

def _run_generation(count: int, territory: str, archetype: Optional[str], seed: Optional[str]):
    global _status, _dataset
    with _lock:
        _status = {"status": "running", "progress": 0, "message": "Started"}
        _dataset = []
    generator = SCDG(seed=seed or f"{territory}-{archetype or 'AUTO'}-{count}")
    for i in range(count):
        try:
            profile = generator.generate_profile({"age": 25 + (i % 30), "territory": territory, "scenario_type": archetype})
            decision_pack = _decide(profile)
            record = {"profile": profile.model_dump(), **decision_pack}
            with _lock:
                _dataset.append(record)
                _status["progress"] = int(((i + 1) / count) * 100)
                _status["message"] = f"Generated {i+1}/{count}"
        except Exception as e:
            with _lock:
                _status["status"] = "error"
                _status["message"] = str(e)
            return
        time.sleep(0.01)
    with _lock:
        _status["status"] = "completed"
        _status["message"] = "Completed"

@router.post("/generate")
async def start_generation(req: GenerateRequest, tasks: BackgroundTasks):
    tasks.add_task(_run_generation, req.count, req.territory, req.archetype, req.seed)
    with _lock:
        st = dict(_status)
    try:
        log_audit(event="synthetic_generate", endpoint="/admin/synthetic/generate", status="accepted", meta={"count": req.count, "territory": req.territory, "archetype": req.archetype})
    except Exception:
        pass
    return {"accepted": True, "status": st}

@router.get("/status")
async def status():
    with _lock:
        st = dict(_status)
    try:
        log_audit(event="synthetic_status", endpoint="/admin/synthetic/status", status=st.get("status", "unknown"), meta={"progress": st.get("progress", 0)})
    except Exception:
        pass
    return st

def _sse_events():
    last = -1
    while True:
        with _lock:
            p = _status.get("progress", 0)
            st = _status.get("status", "idle")
            msg = _status.get("message", "")
        if p != last:
            yield f"data: { {'progress': p, 'status': st, 'message': msg} }\n\n"
            last = p
        if st in ("completed", "error", "idle"):
            break
        time.sleep(0.5)

@router.get("/stream")
async def stream():
    return StreamingResponse(_sse_events(), media_type="text/event-stream")

@router.post("/validate")
async def validate():
    with _lock:
        ds = list(_dataset)
    total = len(ds)
    approved = sum(1 for r in ds if r.get("application", {}).get("decision") == "APPROVED")
    declined = total - approved
    avg_prob = sum(r.get("application", {}).get("probability_good", 0.0) for r in ds) / total if total else 0.0
    result = {
        "total": total,
        "approved": approved,
        "declined": declined,
        "approval_rate": (approved / total) if total else 0.0,
        "avg_probability_good": avg_prob
    }
    try:
        log_audit(event="synthetic_validate", endpoint="/admin/synthetic/validate", status="success", meta=result)
    except Exception:
        pass
    return result
