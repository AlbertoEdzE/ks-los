from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from src.shared.logging import setup_json_logging

from src.api.routers.scdg_router import router as scdg_router
from src.api.routers.agent_router import router as agent_router
from src.api.routers.training_router import router as training_router
from src.api.routers.metrics_router import router as metrics_router
from src.api.routers.observability_router import router as observability_router

# Configure logging
if os.getenv("LOG_JSON", "1") == "1":
    setup_json_logging(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KS LOS Agentic System",
    description="AI-Driven Agentic System for Loan Prequalification and Financial Advisory",
    version="1.0.0"
)

# CORS Middleware (Allow all for development, restrict for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend domain
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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
