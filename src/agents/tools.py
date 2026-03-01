from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from src.agents.data_synthesizer.scdg import SCDG
from src.shared.types import ApplicantCreditProfile

class GenerateProfileInput(BaseModel):
    age: int = Field(description="The applicant's age")
    territory: str = Field(description="The applicant's territory code (e.g., AG, GD, LC)")
    scenario_type: Optional[str] = Field(default=None, description="Optional scenario type like THIN_FILE_YOUNG")

class GenerateProfileTool(BaseTool):
    name: str = "generate_credit_profile"
    description: str = "Generates a synthetic credit profile for a given applicant based on age and territory."
    args_schema: Type[BaseModel] = GenerateProfileInput

    def _run(self, age: int, territory: str, scenario_type: Optional[str] = None) -> str:
        scdg = SCDG(seed=f"{age}-{territory}-{scenario_type}")
        profile = scdg.generate_profile({
            "age": age,
            "territory": territory,
            "scenario_type": scenario_type
        })
        # Return JSON string for easy parsing by downstream nodes
        return profile.model_dump_json()

    async def _arun(self, age: int, territory: str, scenario_type: Optional[str] = None) -> str:
        return self._run(age, territory, scenario_type)
