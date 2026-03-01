from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from src.shared.metrics import request_counter

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("")
def metrics() -> Response:
    request_counter.labels(endpoint="/metrics").inc()
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
