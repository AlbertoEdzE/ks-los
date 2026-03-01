import uuid
import contextvars

_correlation_id = contextvars.ContextVar("correlation_id", default=None)

def set_correlation_id(value: str | None):
    if not value:
        value = str(uuid.uuid4())
    _correlation_id.set(value)
    return value

def get_correlation_id() -> str | None:
    return _correlation_id.get()
