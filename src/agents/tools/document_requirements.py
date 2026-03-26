"""
Document Requirements Tool for Agentic Orchestrator

Generates context-aware document checklists based on:
- Loan type (home, auto, personal, business)
- Employment type (salaried, self-employed, contractor)
- Loan amount (affects documentation requirements)
- Caribbean regional requirements

Usage:
    tool = DocumentRequirementsTool()
    checklist = tool.run(
        loan_type="home_purchase",
        employment_type="salaried",
        loan_amount=400000
    )
"""

from typing import List, Dict, Any, Optional, Type, ClassVar
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from src.agents.orchestrator import DocumentsChecklist


class DocumentRequirementsInput(BaseModel):
    """Input schema for document requirements tool"""
    loan_type: str = Field(description="Type of loan (home_purchase, auto, personal, business)")
    employment_type: str = Field(description="Employment type (salaried, self-employed, contractor)")
    loan_amount: Optional[float] = Field(default=None, description="Loan amount in USD")
    property_value: Optional[float] = Field(default=None, description="Property value (for home loans)")


class DocumentRequirementsTool(BaseTool):
    """
    Generate context-aware document requirements checklist.
    
    This tool generates a tailored list of required documents based on:
    1. Loan type (different loans need different docs)
    2. Employment type (salaried vs self-employed have different requirements)
    3. Loan amount (high-value loans need more documentation)
    4. Caribbean regional requirements (NIS/NI, IRD, etc.)
    
    Features:
    - Caribbean-specific document awareness
    - Tiered requirements (required vs optional)
    - Loan amount-based thresholds
    - Employment-specific requirements
    
    Usage:
        tool = DocumentRequirementsTool()
        checklist = tool.run(
            loan_type="home_purchase",
            employment_type="salaried",
            loan_amount=400000
        )
        
        # Returns DocumentsChecklist with:
        # - identity: ID, proof of address
        # - income: job letter, pay slips, bank statements
        # - property: sale agreement, valuation (for home loans)
    """
    
    name: str = "generate_document_requirements"
    description: str = (
        "Generates a tailored document checklist for a loan application. "
        "Returns required documents based on loan type, employment type, and loan amount. "
        "Includes Caribbean-specific requirements like NIS/NI records and IRD documents."
    )
    args_schema: Type[BaseModel] = DocumentRequirementsInput
    
    # Caribbean-specific document knowledge (ClassVar for Pydantic compatibility)
    CARIBBEAN_DOCUMENTS: ClassVar[Dict[str, Any]] = {
        "identity": [
            {"name": "Valid National ID or Passport", "description": "Government-issued photo ID", "required": True},
            {"name": "Proof of Address", "description": "Utility bill or bank statement (last 3 months)", "required": True},
            {"name": "NIS/NI Number Card", "description": "Social security identification", "required": False},
        ],
        "income_salaried": [
            {"name": "Job Letter", "description": "Employment confirmation letter from current employer (dated within 3 months)", "required": True},
            {"name": "Pay Slips", "description": "Last 3 months' pay slips", "required": True},
            {"name": "Bank Statements", "description": "Last 6 months' personal bank statements", "required": True},
            {"name": "NIS/NI Contributions Record", "description": "Social security contribution history", "required": False},
            {"name": "Tax Compliance Certificate", "description": "IRD tax clearance (if applicable)", "required": False},
        ],
        "income_self_employed": [
            {"name": "Business Registration Certificate", "description": "Certificate of incorporation or business license", "required": True},
            {"name": "Financial Statements", "description": "Last 2 years' audited financial statements", "required": True},
            {"name": "Tax Returns", "description": "Last 2 years' tax returns with IRD stamp", "required": True},
            {"name": "Bank Statements", "description": "Last 6 months' business bank statements", "required": True},
            {"name": "Bank Statements", "description": "Last 6 months' personal bank statements", "required": False},
            {"name": "Articles of Incorporation", "description": "Company registration documents", "required": False},
        ],
        "home_loan": [
            {"name": "Sale Agreement", "description": "Signed purchase agreement or contract of sale", "required": True},
            {"name": "Property Valuation Report", "description": "Professional valuation by approved valuer", "required": True},
            {"name": "Title Deed", "description": "Property title search and legal due diligence report", "required": True},
            {"name": "Surveyor's Report", "description": "Land survey report", "required": False},
            {"name": "Proof of Down Payment", "description": "Bank statements showing down payment funds", "required": True},
            {"name": "Building Insurance Quote", "description": "Insurance quotation for the property", "required": False},
        ],
        "auto_loan": [
            {"name": "Pro-forma Invoice", "description": "Dealer invoice or quotation", "required": True},
            {"name": "Vehicle Registration", "description": "Registration document (if used vehicle)", "required": False},
            {"name": "Insurance Quotation", "description": "Comprehensive insurance quote", "required": True},
            {"name": "Driver's License", "description": "Valid driver's license", "required": False},
        ],
        "high_value_thresholds": {
            "home": 2000000,  # USD - above this needs extra docs
            "auto": 750000,   # USD
            "personal": 500000,  # USD
        },
        "high_value_extra": [
            {"name": "Additional Collateral Documentation", "description": "Extra collateral may be required for high-value loans", "required": False},
            {"name": "Character Reference Letters", "description": "Professional or community references", "required": False},
            {"name": "Enhanced Due Diligence", "description": "Additional KYC/AML documentation", "required": True},
        ],
    }
    
    def _run(
        self,
        loan_type: str,
        employment_type: str,
        loan_amount: Optional[float] = None,
        property_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate document requirements checklist.
        
        Args:
            loan_type: Type of loan
            employment_type: Employment status
            loan_amount: Loan amount (affects requirements)
            property_value: Property value (for home loans)
            
        Returns:
            DocumentsChecklist with categorized requirements
        """
        # Normalize inputs
        loan_type_lower = loan_type.lower()
        employment_type_lower = employment_type.lower()
        
        # Build checklist
        checklist = DocumentsChecklist()
        
        # 1. Identity documents (always required)
        checklist.identity = self.CARIBBEAN_DOCUMENTS["identity"]
        
        # 2. Income documents (based on employment type)
        if employment_type_lower in ["salaried", "employed", "government"]:
            checklist.income = self.CARIBBEAN_DOCUMENTS["income_salaried"]
        elif employment_type_lower in ["self-employed", "business_owner", "freelance"]:
            checklist.income = self.CARIBBEAN_DOCUMENTS["income_self_employed"]
        else:  # contractor, etc.
            # Default to self-employed requirements
            checklist.income = self.CARIBBEAN_DOCUMENTS["income_self_employed"]
        
        # 3. Loan-type specific documents
        if any(term in loan_type_lower for term in ["home", "house", "property", "mortgage"]):
            checklist.property = self.CARIBBEAN_DOCUMENTS["home_loan"]
        elif any(term in loan_type_lower for term in ["auto", "car", "vehicle"]):
            checklist.vehicle = self.CARIBBEAN_DOCUMENTS["auto_loan"]
        
        # 4. High-value loan extra requirements
        if loan_amount:
            if self._is_high_value(loan_type_lower, loan_amount):
                # Add extra requirements
                checklist.income = checklist.income + self.CARIBBEAN_DOCUMENTS["high_value_extra"]
        
        # Convert to dict for JSON serialization
        return checklist.model_dump()
    
    async def _arun(
        self,
        loan_type: str,
        employment_type: str,
        loan_amount: Optional[float] = None,
        property_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Async version - runs sync in thread pool"""
        import asyncio
        return await asyncio.to_thread(
            self._run,
            loan_type,
            employment_type,
            loan_amount,
            property_value
        )
    
    def _is_high_value(self, loan_type: str, loan_amount: float) -> bool:
        """Check if loan amount exceeds high-value threshold"""
        thresholds = self.CARIBBEAN_DOCUMENTS["high_value_thresholds"]
        
        if "home" in loan_type or "mortgage" in loan_type:
            return loan_amount > thresholds["home"]
        elif "auto" in loan_type or "vehicle" in loan_type:
            return loan_amount > thresholds["auto"]
        else:
            return loan_amount > thresholds["personal"]


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def generate_document_requirements(
    loan_type: str,
    employment_type: str,
    loan_amount: Optional[float] = None
) -> DocumentsChecklist:
    """
    Convenience function to generate document requirements.
    
    Args:
        loan_type: Type of loan
        employment_type: Employment status
        loan_amount: Loan amount (optional)
        
    Returns:
        DocumentsChecklist with requirements
    """
    tool = DocumentRequirementsTool()
    result = tool.run(
        loan_type=loan_type,
        employment_type=employment_type,
        loan_amount=loan_amount
    )
    return DocumentsChecklist(**result)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "DocumentRequirementsTool",
    "DocumentRequirementsInput",
    "generate_document_requirements",
]
