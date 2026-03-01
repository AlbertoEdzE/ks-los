import json
import time
import logging
from typing import Any, Dict, Optional
from src.shared.correlation import get_correlation_id

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
