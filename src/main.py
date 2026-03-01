from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.api.routers.scdg_router import router as scdg_router
from src.api.routers.agent_router import router as agent_router

# Configure logging
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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
