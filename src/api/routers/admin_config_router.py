from fastapi import APIRouter
from typing import Dict
import redis

router = APIRouter(prefix="/admin/config", tags=["admin_config"])

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
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
    return {"value": _get_flag()}
