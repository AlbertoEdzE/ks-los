from fastapi import Header, HTTPException

import src.shared.auth as rbac_auth


OFFICER_HEADER = "x-officer-role"
OFFICER_TOKEN = "loan-officer-access"


async def require_viewer_role(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    if not rbac_auth.ENFORCE_RBAC or not rbac_auth.API_KEYS:
        return True
    if not x_api_key or x_api_key not in rbac_auth.API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


def is_officer_request(x_api_key: str | None, x_officer_role: str | None) -> bool:
    if rbac_auth.ENFORCE_RBAC and rbac_auth.API_KEYS:
        if not x_api_key or x_api_key not in rbac_auth.API_KEYS:
            return False
        role = rbac_auth.API_KEYS[x_api_key]
        return rbac_auth.ROLE_ORDER[role] >= rbac_auth.ROLE_ORDER["operator"]
    return x_officer_role == OFFICER_TOKEN


async def require_officer_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_officer_role: str | None = Header(default=None, alias=OFFICER_HEADER),
):
    if rbac_auth.ENFORCE_RBAC and rbac_auth.API_KEYS:
        if not x_api_key or x_api_key not in rbac_auth.API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        role = rbac_auth.API_KEYS[x_api_key]
        if rbac_auth.ROLE_ORDER[role] < rbac_auth.ROLE_ORDER["operator"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    if x_officer_role != OFFICER_TOKEN:
        raise HTTPException(status_code=403, detail="Officer access required")
    return True
