from fastapi import Header, HTTPException


OFFICER_HEADER = "x-officer-role"
OFFICER_TOKEN = "loan-officer-access"


async def require_officer_role(x_officer_role: str | None = Header(default=None, alias=OFFICER_HEADER)):
    if x_officer_role != OFFICER_TOKEN:
        raise HTTPException(status_code=403, detail="Officer access required")
    return True

