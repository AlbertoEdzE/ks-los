from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from src.shared.logging import setup_json_logging
from src.shared.correlation import get_correlation_id, set_correlation_id
from src.shared.metrics import request_counter, request_errors_total, request_latency_seconds
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry import trace

from src.api.routers.scdg_router import router as scdg_router
from src.api.routers.agent_router import router as agent_router
from src.api.routers.training_router import router as training_router
from src.api.routers.metrics_router import router as metrics_router
from src.api.routers.observability_router import router as observability_router
from src.api.routers.explain_router import router as explain_router
from src.api.routers.admin_synthetic_router import router as admin_synthetic_router
from src.api.routers.chat_support_router import router as chat_support_router
from src.api.routers.admin_config_router import router as admin_config_router
from src.api.routers.admin_seed_router import router as admin_seed_router
from src.api.routers.model_manage_router import router as model_manage_router
from src.api.routers.v2_conversations_router import router as v2_conversations_router
from src.api.routers.v2_phases_router import router as v2_phases_router
from src.api.routers.v2_loans_router import router as v2_loans_router
from src.api.routers.v2_catalog_products_router import router as v2_catalog_products_router

# Configure logging
if os.getenv("LOG_JSON", "1") == "1":
    setup_json_logging(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# OpenTelemetry exporter initialization (optional via OTLP_URL)
OTLP_URL = os.getenv("OTLP_URL")
if OTLP_URL:
    resource = Resource(attributes={"service.name": "ks-los-api", "environment": os.getenv("ENV", "local")})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_URL, insecure=True)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KS LOS Agentic System",
    description="AI-Driven Agentic System for Loan Prequalification and Financial Advisory",
    version="1.0.0"
)

# CORS Middleware (Allow all for development, restrict for production)
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:5178",
    "http://localhost:5179",
    "http://localhost:5180",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://127.0.0.1:5177",
    "http://127.0.0.1:5178",
    "http://127.0.0.1:5179",
    "http://127.0.0.1:5180",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # In production, restrict to frontend domain
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(scdg_router)
app.include_router(agent_router)
app.include_router(training_router)
app.include_router(metrics_router)
app.include_router(observability_router)
app.include_router(explain_router)
app.include_router(admin_synthetic_router)
app.include_router(chat_support_router)
app.include_router(admin_config_router)
app.include_router(admin_seed_router)
app.include_router(model_manage_router)
app.include_router(v2_conversations_router)
app.include_router(v2_phases_router)
app.include_router(v2_loans_router)
app.include_router(v2_catalog_products_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    cid = get_correlation_id() or set_correlation_id(None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "correlationId": cid},
        headers={"X-Correlation-ID": cid},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError):
    cid = get_correlation_id() or set_correlation_id(None)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "correlationId": cid},
        headers={"X-Correlation-ID": cid},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, __: Exception):
    cid = get_correlation_id() or set_correlation_id(None)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "correlationId": cid},
        headers={"X-Correlation-ID": cid},
    )


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID")
    correlation_id = set_correlation_id(cid)
    endpoint = request.url.path
    request_counter.labels(endpoint=endpoint).inc()
    import time
    start = time.monotonic()
    tracer = trace.get_tracer("api")
    try:
        with tracer.start_as_current_span(f"http_request:{endpoint}"):
            response = await call_next(request)
    except Exception:
        request_errors_total.labels(endpoint=endpoint).inc()
        raise
    duration = time.monotonic() - start
    request_latency_seconds.labels(endpoint=endpoint).observe(duration)
    response.headers["X-Correlation-ID"] = correlation_id
    # Inject traceparent header
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id and ctx.span_id:
        version = "00"
        trace_id = format(ctx.trace_id, "032x")
        span_id = format(ctx.span_id, "016x")
        flags = "01" if ctx.trace_flags & 0x01 else "00"
        response.headers["traceparent"] = f"{version}-{trace_id}-{span_id}-{flags}"
    return response
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
