from fastapi import APIRouter, Depends, Query
from typing import Dict, Any
import uuid
import redis
from datetime import datetime
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from src.agents.data_synthesizer.scdg import SCDG
from src.api.routers.v2_auth import require_officer_role
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
async def seed_demo_names(reset: bool = Query(False), count: int = Query(500)) -> Dict[str, Any]:
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
    _: bool = Depends(require_officer_role),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    def _phase_id(name: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:phase:{name}"))

    def _product_id(code: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ks-los:v2:product:{code}"))

    try:
        from src.api.routers.v2_phases_router import DEFAULT_PHASES
        from src.api.routers.v2_catalog_products_router import DEFAULT_PRODUCTS

        if reset:
            db.execute(delete(LoanProductCatalog))
            db.execute(delete(LoanPhase))
            db.commit()

        existing_phase_names = set(db.execute(select(LoanPhase.name)).scalars().all())
        phases_added = 0
        for phase in DEFAULT_PHASES:
            if phase["name"] in existing_phase_names:
                continue
            db.add(LoanPhase(id=_phase_id(phase["name"]), **phase))
            phases_added += 1
        db.commit()

        existing_product_codes = set(db.execute(select(LoanProductCatalog.code)).scalars().all())
        products_added = 0
        for prod in DEFAULT_PRODUCTS:
            if prod["code"] in existing_product_codes:
                continue
            db.add(LoanProductCatalog(id=_product_id(prod["code"]), **prod))
            products_added += 1
        db.commit()

        phases_total = db.execute(select(LoanPhase.id)).scalars().all()
        products_total = db.execute(select(LoanProductCatalog.id)).scalars().all()

        meta = {
            "reset": reset,
            "phases_added": phases_added,
            "products_added": products_added,
            "phases_total": len(phases_total),
            "products_total": len(products_total),
        }
        log_audit(event="seed_v2_baseline", endpoint="/admin/seed/v2-baseline", status="success", meta=meta)
        return meta
    except Exception as e:
        db.rollback()
        log_audit(event="seed_v2_baseline", endpoint="/admin/seed/v2-baseline", status="error", meta={"error": str(e)})
        return {"error": str(e)}
