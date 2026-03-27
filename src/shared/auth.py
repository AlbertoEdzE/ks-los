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
DEV_OFFICER_TOKEN = os.getenv("DEV_OFFICER_TOKEN", "loan-officer-access")
DEV_ADMIN_TOKEN = os.getenv("DEV_ADMIN_TOKEN", "admin-access")

def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None

def get_presented_token(x_api_key: str | None, authorization: str | None) -> str | None:
    bearer = _parse_bearer_token(authorization)
    return bearer or x_api_key

def get_role_for_token(token: str) -> str | None:
    return API_KEYS.get(token)

def require_role(required: str):
    async def _dep(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ):
        if not ENFORCE_RBAC or not API_KEYS:
            if required == "viewer":
                return True
            token = get_presented_token(x_api_key, authorization)
            if required == "operator":
                if token in (DEV_OFFICER_TOKEN, DEV_ADMIN_TOKEN):
                    return True
                raise HTTPException(status_code=403, detail="Officer access required")
            if required == "admin":
                if token == DEV_ADMIN_TOKEN:
                    return True
                raise HTTPException(status_code=403, detail="Admin access required")
            return True
        token = get_presented_token(x_api_key, authorization)
        if not token or token not in API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_role = API_KEYS[token]
        if ROLE_ORDER[user_role] < ROLE_ORDER[required]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    return _dep


def is_officer_request(x_api_key: str | None, authorization: str | None) -> bool:
    token = get_presented_token(x_api_key, authorization)
    if ENFORCE_RBAC and API_KEYS:
        if not token or token not in API_KEYS:
            return False
        role = API_KEYS[token]
        return ROLE_ORDER[role] >= ROLE_ORDER["operator"]
    return token in (DEV_OFFICER_TOKEN, DEV_ADMIN_TOKEN)


require_viewer_role = require_role("viewer")


async def require_officer_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    if ENFORCE_RBAC and API_KEYS:
        token = get_presented_token(x_api_key, authorization)
        if not token or token not in API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        role = API_KEYS[token]
        if ROLE_ORDER[role] < ROLE_ORDER["operator"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    token = get_presented_token(x_api_key, authorization)
    if token not in (DEV_OFFICER_TOKEN, DEV_ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Officer access required")
    return True


async def require_admin_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    if ENFORCE_RBAC and API_KEYS:
        token = get_presented_token(x_api_key, authorization)
        if not token or token not in API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        role = API_KEYS[token]
        if ROLE_ORDER[role] < ROLE_ORDER["admin"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    token = get_presented_token(x_api_key, authorization)
    if token != DEV_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True
