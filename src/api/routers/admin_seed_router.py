from fastapi import APIRouter, Depends, Query
from typing import Dict, Any
import redis
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from src.agents.data_synthesizer.scdg import SCDG
from src.shared.auth import require_role
from src.shared.audit import log_audit

from src.shared.db import LoanPhase, LoanProductCatalog, get_db
router = APIRouter(prefix="/admin/seed", tags=["admin_seed"])


try:
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.ping()
except Exception:
    class MockRedis:
        def __init__(self):
            self.store = {}

        def get(self, k):
            return self.store.get(k)

        def set(self, k, v):
            self.store[k] = v

        def delete(self, k):
            if k in self.store:
                del self.store[k]

        def exists(self, k):
            return k in self.store

        def rpush(self, k, *v):
            l = self.store.get(k, [])
            if not isinstance(l, list):
                l = []
            l.extend(list(v))
            self.store[k] = l

        def lrange(self, k, s, e):
            l = self.store.get(k, [])
            if e == -1:
                return l[s:]
            return l[s : e + 1]

        def ping(self):
            return True

    r = MockRedis()
DEMO_NAMES_KEY = "demo:names"

def _seed_names(count: int = 500) -> int:
    gen = SCDG(seed=f"seed-{datetime.utcnow().isoformat()}")
    names = set()
    for i in range(count):
        profile = gen.generate_profile({"age": 25 + (i % 30), "territory": "ECCU"})
        names.add(profile.identity.full_name)
    # Ensure deterministic common prefixes exist for testing stability
    fixed = {"John Aaron", "Joan Anderson", "Joseph Alvarez"}
    names.update(fixed)
    # idempotent add: ensure list contains unique names
    existing = set(r.lrange(DEMO_NAMES_KEY, 0, -1))
    to_add = [n for n in names if n not in existing]
    if to_add:
        # maintain deterministic order
        for n in sorted(to_add):
            r.rpush(DEMO_NAMES_KEY, n)
    return len(r.lrange(DEMO_NAMES_KEY, 0, -1))

@router.post("/demo-names")
async def seed_demo_names(
    reset: bool = Query(False),
    count: int = Query(500),
    _: bool = Depends(require_role("admin")),
) -> Dict[str, Any]:
    try:
        if reset:
            r.delete(DEMO_NAMES_KEY)
        total = _seed_names(count=count)
        log_audit(event="seed_demo_names", endpoint="/admin/seed/demo-names", status="success", meta={"reset": reset, "total": total})
        return {"total": total, "reset": reset}
    except Exception as e:
        log_audit(event="seed_demo_names", endpoint="/admin/seed/demo-names", status="error", meta={"error": str(e)})
        return {"error": str(e)}


@router.post("/v2-baseline")
async def seed_v2_baseline(
    reset: bool = Query(False),
    _: bool = Depends(require_role("operator")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    from src.api.routers.v2_phases_router import DEFAULT_PHASES
    from src.api.routers.v2_catalog_products_router import DEFAULT_PRODUCTS

    try:
        phases_added = 0
        products_added = 0

        if reset:
            db.query(LoanPhase).delete()
            db.query(LoanProductCatalog).delete()
            db.commit()

        for p in DEFAULT_PHASES:
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:phase:{p['name']}"))
            existing = db.get(LoanPhase, pid)
            if existing is not None:
                continue
            db.add(
                LoanPhase(
                    id=pid,
                    name=p["name"],
                    description=p.get("description"),
                    sort_order=int(p["sort_order"]),
                    is_active=True,
                    color=p.get("color"),
                    icon=p.get("icon"),
                )
            )
            phases_added += 1

        for p in DEFAULT_PRODUCTS:
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:product:{p['code']}"))
            existing = db.get(LoanProductCatalog, pid)
            if existing is not None:
                continue
            db.add(
                LoanProductCatalog(
                    id=pid,
                    name=p["name"],
                    code=p["code"],
                    category=p["category"],
                    description=p.get("description"),
                    min_amount=p.get("min_amount"),
                    max_amount=p.get("max_amount"),
                    min_tenure_months=p.get("min_tenure_months"),
                    max_tenure_months=p.get("max_tenure_months"),
                    base_interest_rate=p.get("base_interest_rate"),
                    max_interest_rate=p.get("max_interest_rate"),
                    processing_fee_percent=p.get("processing_fee_percent"),
                    prepayment_penalty=p.get("prepayment_penalty"),
                    min_credit_score=p.get("min_credit_score"),
                    max_ltv=p.get("max_ltv"),
                    min_income=p.get("min_income"),
                    collateral_required=bool(p.get("collateral_required", False)),
                    insurance_required=bool(p.get("insurance_required", False)),
                    required_documents=p.get("required_documents"),
                    eligibility_criteria=p.get("eligibility_criteria"),
                    features=p.get("features"),
                    target_segment=p.get("target_segment"),
                    risk_grade=p.get("risk_grade"),
                    status=p.get("status") or "draft",
                    icon=p.get("icon"),
                    color=p.get("color"),
                )
            )
            products_added += 1

        db.commit()

        phases_total = int(db.query(LoanPhase).count())
        products_total = int(db.query(LoanProductCatalog).count())

        payload = {
            "reset": reset,
            "phases_total": phases_total,
            "products_total": products_total,
            "phases_added": phases_added,
            "products_added": products_added,
        }
        log_audit(event="seed_v2_baseline", endpoint="/admin/seed/v2-baseline", status="success", meta=payload)
        return payload
    except Exception as e:
        db.rollback()
        log_audit(event="seed_v2_baseline", endpoint="/admin/seed/v2-baseline", status="error", meta={"reset": reset, "error": str(e)})
        return {"error": str(e)}
