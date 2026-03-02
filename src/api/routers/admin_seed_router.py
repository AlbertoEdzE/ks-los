from fastapi import APIRouter, Query
from typing import Dict, Any
import redis
from datetime import datetime
from src.agents.data_synthesizer.scdg import SCDG
from src.shared.audit import log_audit

router = APIRouter(prefix="/admin/seed", tags=["admin_seed"])

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
DEMO_NAMES_KEY = "demo:names"

def _seed_names(count: int = 500) -> int:
    gen = SCDG(seed=f"seed-{datetime.utcnow().isoformat()}")
    names = set()
    for i in range(count):
        profile = gen.generate_profile({"age": 25 + (i % 30), "territory": "ECCU"})
        names.add(profile.identity.full_name)
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
