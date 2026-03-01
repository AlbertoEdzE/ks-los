import os
from typing import Dict
from fastapi import HTTPException, Header

ROLE_ORDER = {"viewer": 0, "operator": 1, "admin": 2}

def _load_api_keys() -> Dict[str, str]:
    raw = os.getenv("API_KEYS", "")
    # Format: key1:admin,key2:operator
    mapping: Dict[str, str] = {}
    for pair in [p for p in raw.split(",") if p.strip()]:
        try:
            key, role = pair.split(":")
            role = role.strip().lower()
            if role in ROLE_ORDER:
                mapping[key.strip()] = role
        except ValueError:
            continue
    return mapping

API_KEYS = _load_api_keys()
ENFORCE_RBAC = os.getenv("ENFORCE_RBAC", "0") == "1"

def require_role(required: str):
    async def _dep(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
        if not ENFORCE_RBAC or not API_KEYS:
            return True
        if not x_api_key or x_api_key not in API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_role = API_KEYS[x_api_key]
        if ROLE_ORDER[user_role] < ROLE_ORDER[required]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    return _dep
