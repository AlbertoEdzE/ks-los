from fastapi import APIRouter
from typing import Dict
import redis
from src.shared.audit import log_audit

router = APIRouter(prefix="/admin/config", tags=["admin_config"])

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

        def ping(self):
            return True

    r = MockRedis()
SUGGESTIONS_KEY = "config:suggestions_enabled"

def _get_flag() -> bool:
    val = r.get(SUGGESTIONS_KEY)
    if val is None:
        r.set(SUGGESTIONS_KEY, "1")
        return True
    return val == "1"

@router.get("/suggestions_enabled")
async def get_suggestions_enabled() -> Dict[str, bool]:
    return {"value": _get_flag()}

@router.post("/suggestions_enabled")
async def set_suggestions_enabled(value: bool) -> Dict[str, bool]:
    r.set(SUGGESTIONS_KEY, "1" if value else "0")
    try:
        log_audit(event="toggle_suggestions", endpoint="/admin/config/suggestions_enabled", status="success", meta={"value": value})
    except Exception:
        pass
    return {"value": _get_flag()}
