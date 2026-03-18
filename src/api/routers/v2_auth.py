import os

from fastapi import Header, HTTPException

import src.shared.auth as rbac_auth


DEV_OFFICER_TOKEN = os.getenv("DEV_OFFICER_TOKEN", "loan-officer-access")
DEV_ADMIN_TOKEN = os.getenv("DEV_ADMIN_TOKEN", "admin-access")


async def require_viewer_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    if not rbac_auth.ENFORCE_RBAC or not rbac_auth.API_KEYS:
        return True
    token = rbac_auth.get_presented_token(x_api_key, authorization)
    if not token or token not in rbac_auth.API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


def is_officer_request(x_api_key: str | None, authorization: str | None) -> bool:
    if rbac_auth.ENFORCE_RBAC and rbac_auth.API_KEYS:
        token = rbac_auth.get_presented_token(x_api_key, authorization)
        if not token or token not in rbac_auth.API_KEYS:
            return False
        role = rbac_auth.API_KEYS[token]
        return rbac_auth.ROLE_ORDER[role] >= rbac_auth.ROLE_ORDER["operator"]
    token = rbac_auth.get_presented_token(x_api_key, authorization)
    return token in (DEV_OFFICER_TOKEN, DEV_ADMIN_TOKEN)


async def require_officer_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    if rbac_auth.ENFORCE_RBAC and rbac_auth.API_KEYS:
        token = rbac_auth.get_presented_token(x_api_key, authorization)
        if not token or token not in rbac_auth.API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        role = rbac_auth.API_KEYS[token]
        if rbac_auth.ROLE_ORDER[role] < rbac_auth.ROLE_ORDER["operator"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    token = rbac_auth.get_presented_token(x_api_key, authorization)
    if token not in (DEV_OFFICER_TOKEN, DEV_ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Officer access required")
    return True


async def require_admin_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    if rbac_auth.ENFORCE_RBAC and rbac_auth.API_KEYS:
        token = rbac_auth.get_presented_token(x_api_key, authorization)
        if not token or token not in rbac_auth.API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")
        role = rbac_auth.API_KEYS[token]
        if rbac_auth.ROLE_ORDER[role] < rbac_auth.ROLE_ORDER["admin"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    token = rbac_auth.get_presented_token(x_api_key, authorization)
    if token != DEV_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True
