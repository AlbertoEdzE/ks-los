from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from src.agents.data_synthesizer.scdg import SCDG
from src.shared.types import ApplicantCreditProfile

class GenerateProfileInput(BaseModel):
    full_name: str = Field(description="The applicant's full name")
    age: int = Field(description="The applicant's age")
    territory: str = Field(description="The applicant's territory code (e.g., AG, GD, LC)")
    scenario_type: Optional[str] = Field(default=None, description="Optional scenario type like THIN_FILE_YOUNG")

class GenerateProfileTool(BaseTool):
    name: str = "generate_credit_profile"
    description: str = "The 'Organizer' tool. Parses provided document text (Bank Statements/IDs) to extract and generate a structured credit profile."
    args_schema: Type[BaseModel] = GenerateProfileInput

    def _run(self, full_name: str, age: int, territory: str, scenario_type: Optional[str] = None) -> str:
        scdg = SCDG(seed=f"{full_name}-{age}-{territory}-{scenario_type}")
        profile = scdg.generate_profile({
            "age": age,
            "territory": territory,
            "scenario_type": scenario_type
        })
        # Override name with the one provided by user
        profile.identity.full_name = full_name
        # Return JSON string for easy parsing by downstream nodes
        return profile.model_dump_json()

    async def _arun(self, full_name: str, age: int, territory: str, scenario_type: Optional[str] = None) -> str:
        return self._run(full_name, age, territory, scenario_type)
