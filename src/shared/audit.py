import json
import time
import logging
from typing import Any, Dict, Optional
from src.shared.correlation import get_correlation_id
from src.shared.db import AuditEvent, create_session

logger = logging.getLogger("audit")

def log_audit(event: str, endpoint: str, status: str, meta: Optional[Dict[str, Any]] = None):
    payload = {
        "ts": time.time(),
        "event": event,
        "endpoint": endpoint,
        "status": status,
        "correlation_id": get_correlation_id(),
        "meta": meta or {},
    }
    try:
        logger.info(json.dumps(payload))
    except Exception:
        pass

    try:
        db = create_session()
        try:
            db.add(
                AuditEvent(
                    event=event,
                    endpoint=endpoint,
                    status=status,
                    correlation_id=payload["correlation_id"],
                    meta=payload["meta"],
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
