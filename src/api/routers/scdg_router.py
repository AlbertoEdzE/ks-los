from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from src.agents.data_synthesizer.scdg import SCDG
from src.shared.types import ApplicantCreditProfile

router = APIRouter(prefix="/scdg", tags=["Synthetic Data"])

class SCDGRequest(BaseModel):
    age: int
    territory: str = "AG"
    scenario_type: Optional[str] = None
    seed: Optional[str] = None

@router.post("/generate", response_model=ApplicantCreditProfile)
async def generate_profile(request: SCDGRequest):
    """
    Generates a synthetic credit profile based on the request parameters.
    If no seed is provided, a random one is generated.
    """
    seed = request.seed or f"{request.age}-{request.territory}-{request.scenario_type}-{str(hash(str(request)))}"
    
    generator = SCDG(seed=seed)
    
    applicant_data = {
        "age": request.age,
        "territory": request.territory,
        "scenario_type": request.scenario_type
    }
    
    try:
        profile = generator.generate_profile(applicant_data)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
