"""
LNAI-Style Orchestrator Agent for KS-LOS v2.0

This orchestrator manages the complete borrower conversation flow,
mimicking the Loan-Navigator-AI approach with structured XML tags
and sequential card revelations.

Conversation Flow:
1. Intent Capture (purpose, identity)
2. Financial Context (employment, income, amount, debts)
3. Loan Snapshot + Recommendations (combined output)
4. Application Submission (contact info)
5. STP Processing (bureau pull, checkpoints, affordability)
6. Terms Acceptance (signature)
7. Disbursement (confirmation)
"""

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import re


class ConversationStage(str):
    """Conversation state machine stages"""
    INTENT_CAPTURE = "intent_capture"
    FINANCIAL_CONTEXT = "financial_context"
    READY_FOR_METRICS = "ready_for_metrics"
    READY_FOR_RECOMMENDATION = "ready_for_recommendation"
    APPLICANT_IDENTITY = "applicant_identity"
    APPLICATION_SUBMITTED = "application_submitted"
    STP_PROCESSING = "stp_processing"
    TERMS_ACCEPTANCE = "terms_acceptance"
    DISBURSEMENT = "disbursement"
    COMPLETED = "completed"


class CapturedContext(BaseModel):
    """Extracted loan context from conversation"""
    purpose: Optional[str] = None
    property_value: Optional[float] = None
    property_currency: str = "USD"
    loan_amount: Optional[float] = None
    down_payment: Optional[float] = None
    down_payment_currency: str = "USD"
    employment_type: Optional[str] = None  # "salaried", "self-employed", "contractor"
    monthly_income: Optional[float] = None
    income_currency: str = "USD"
    existing_debts: Optional[float] = None
    loan_tenure_years: Optional[int] = None
    preferred_term: Optional[str] = None  # "lower_monthly" or "faster_repayment"
    credit_score: Optional[int] = None
    credit_history: Optional[str] = None
    has_existing_debts: Optional[bool] = None
    property_location: Optional[str] = None
    borrower_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class LoanSnapshot(BaseModel):
    """Computed loan metrics"""
    loan_amount: float
    down_payment: float
    property_value: float
    estimated_emi: float
    tenure_years: int
    interest_rate: float
    total_interest: float
    total_repayment: float
    ltv_ratio: float
    foir_ratio: Optional[float] = None
    currency: str = "USD"


class LoanRecommendation(BaseModel):
    """Single loan option"""
    name: str
    type: Literal["aggressive", "balanced", "conservative"]
    interest_rate: float
    tenure_years: int
    monthly_emi: float
    total_interest: float
    total_repayment: float
    pros: List[str]
    cons: List[str]
    recommended: bool = False


class DocumentsChecklist(BaseModel):
    """Required documents by category"""
    identity: List[Dict[str, str]] = []
    income: List[Dict[str, str]] = []
    business: List[Dict[str, str]] = []  # For self-employed
    property: List[Dict[str, str]] = []  # For home loans
    vehicle: List[Dict[str, str]] = []   # For auto loans


class STPCheckpoint(BaseModel):
    """Single STP checkpoint"""
    name: str
    status: Literal["pending", "processing", "passed", "failed"] = "pending"
    details: Optional[str] = None


class OrchestratorState(BaseModel):
    """Complete orchestrator state"""
    model_config = {"arbitrary_types_allowed": True}
    
    stage: ConversationStage = ConversationStage.INTENT_CAPTURE
    captured_context: CapturedContext = Field(default_factory=CapturedContext)
    loan_snapshot: Optional[LoanSnapshot] = None
    recommendations: List[LoanRecommendation] = []
    selected_recommendation: Optional[LoanRecommendation] = None
    documents_checklist: Optional[DocumentsChecklist] = None
    stp_checkpoints: List[STPCheckpoint] = []
    stp_completed: bool = False
    stp_approved: bool = False
    bureau_score: Optional[int] = None
    awaiting_acceptance: bool = False
    terms_accepted: bool = False
    disbursement_completed: bool = False
    application_id: Optional[str] = None


class LNAIOrchestrator:
    """
    LNAI-Style Orchestrator
    
    Manages conversation flow with strict pacing:
    - One intent per turn
    - Structured XML tags for data
    - Sequential card revelations
    """
    
    def __init__(self):
        self.state = OrchestratorState()
        self.conversation_history: List[Dict[str, str]] = []
    
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message and return response with metadata
        
        Returns dict with:
        - response: str (natural language response)
        - stage: str (current conversation stage)
        - loan_snapshot: dict (if ready)
        - recommendations: list (if ready)
        - documents_checklist: dict (if submitting)
        - stp_checkpoints: list (if processing)
        - metadata: dict (for UI cards)
        """
        # Add to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Route based on current stage
        if self.state.stage == ConversationStage.INTENT_CAPTURE:
            return self._handle_intent_capture(user_message)
        elif self.state.stage == ConversationStage.FINANCIAL_CONTEXT:
            return self._handle_financial_context(user_message)
        elif self.state.stage == ConversationStage.READY_FOR_METRICS:
            return self._handle_metrics_computation(user_message)
        elif self.state.stage == ConversationStage.READY_FOR_RECOMMENDATION:
            return self._handle_recommendation_selection(user_message)
        elif self.state.stage == ConversationStage.APPLICANT_IDENTITY:
            return self._handle_applicant_identity(user_message)
        elif self.state.stage == ConversationStage.APPLICATION_SUBMITTED:
            return self._handle_application_submission(user_message)
        elif self.state.stage == ConversationStage.STP_PROCESSING:
            return self._handle_stp_processing(user_message)
        elif self.state.stage == ConversationStage.TERMS_ACCEPTANCE:
            return self._handle_terms_acceptance(user_message)
        elif self.state.stage == ConversationStage.DISBURSEMENT:
            return self._handle_disbursement(user_message)
        else:
            return self._handle_completed(user_message)
    
    def _handle_intent_capture(self, message: str) -> Dict[str, Any]:
        """Stage 1: Capture loan purpose and borrower identity"""
        message_lower = message.lower()
        
        # Extract purpose
        if any(word in message_lower for word in ["home", "house", "property", "buy house"]):
            self.state.captured_context.purpose = "home_purchase"
        elif any(word in message_lower for word in ["car", "auto", "vehicle", "buy car"]):
            self.state.captured_context.purpose = "auto"
        elif any(word in message_lower for word in ["personal", "debt", "consolidation"]):
            self.state.captured_context.purpose = "personal"
        elif any(word in message_lower for word in ["business", "commercial"]):
            self.state.captured_context.purpose = "business"
        elif any(word in message_lower for word in ["education", "study", "tuition"]):
            self.state.captured_context.purpose = "education"
        elif any(word in message_lower for word in ["medical", "health"]):
            self.state.captured_context.purpose = "medical"
        
        # Extract property value if mentioned
        property_match = re.search(r'\$?([\d,]+)\s*(?:thousand|k)?\s*(?:usd|eur|xcd)?', message_lower)
        if property_match and "property" in message_lower or "value" in message_lower or "valued" in message_lower:
            value = float(property_match.group(1).replace(',', ''))
            if 'k' in message_lower or 'thousand' in message_lower:
                value *= 1000
            self.state.captured_context.property_value = value
        
        # Extract location
        location_match = re.search(r'in\s+([A-Za-z\s]+?)(?:\.|,|$)', message_lower)
        if location_match:
            self.state.captured_context.property_location = location_match.group(1).strip().title()
        
        # Check if we have enough to move forward
        if self.state.captured_context.purpose:
            # Ask follow-up questions based on what's missing
            if not self.state.captured_context.property_value and self.state.captured_context.purpose == "home_purchase":
                response = (
                    f"Great! A {self.state.captured_context.purpose.replace('_', ' ')} loan is a significant step. "
                    "To help you better:\n\n"
                    "1. What's the property value or purchase price?\n"
                    "2. How much do you have available for a down payment?"
                )
            else:
                # Move to next stage
                self.state.stage = ConversationStage.FINANCIAL_CONTEXT
                response = (
                    f"Perfect! I'm here to help you with your {self.state.captured_context.purpose.replace('_', ' ')} loan.\n\n"
                    "To structure the best options for you, I need to understand your financial situation:\n\n"
                    "1. Are you salaried, self-employed, or a contractor?\n"
                    "2. What is your monthly income before deductions?"
                )
        else:
            response = (
                "I'm here to help you find the right loan. Could you tell me:\n\n"
                "What is the primary purpose of the loan you're looking for?\n\n"
                "For example: home purchase, car loan, personal loan, business loan, education, or medical expenses."
            )
        
        return self._build_response(response)
    
    def _handle_financial_context(self, message: str) -> Dict[str, Any]:
        """Stage 2: Capture employment, income, loan amount, debts"""
        message_lower = message.lower()
        
        # Extract employment type
        if any(word in message_lower for word in ["salaried", "employee", "work for", "employed"]):
            self.state.captured_context.employment_type = "salaried"
        elif any(word in message_lower for word in ["self-employed", "self employed", "business owner", "freelance"]):
            self.state.captured_context.employment_type = "self-employed"
        elif any(word in message_lower for word in ["contractor", "contract", "consultant"]):
            self.state.captured_context.employment_type = "contractor"
        
        # Extract monthly income
        income_match = re.search(r'(?:income|earn|make|salary)[\s$]*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', message_lower)
        if not income_match:
            income_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:per month|monthly|/month)', message_lower)
        if income_match:
            self.state.captured_context.monthly_income = float(income_match.group(1).replace(',', ''))
        
        # Extract loan amount or property value
        amount_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', message_lower)
        if amount_match:
            amount = float(amount_match.group(1).replace(',', ''))
            # Check if it's down payment
            if "down payment" in message_lower or "downpayment" in message_lower:
                self.state.captured_context.down_payment = amount
            # Check if it's loan amount
            elif "loan" in message_lower or "borrow" in message_lower:
                self.state.captured_context.loan_amount = amount
            # Check if it's property value
            elif "property" in message_lower or "value" in message_lower or "priced" in message_lower:
                self.state.captured_context.property_value = amount
        
        # Extract tenure preference
        tenure_match = re.search(r'(\d+)\s*(?:year|yr)', message_lower)
        if tenure_match:
            self.state.captured_context.loan_tenure_years = int(tenure_match.group(1))
        
        # Extract debt preference
        if any(word in message_lower for word in ["no debt", "no debts", "no existing", "none", "nothing"]):
            self.state.captured_context.has_existing_debts = False
            self.state.captured_context.existing_debts = 0
        elif "debt" in message_lower or "obligation" in message_lower or "repayment" in message_lower:
            self.state.captured_context.has_existing_debts = True
            debt_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*)', message_lower)
            if debt_match:
                self.state.captured_context.existing_debts = float(debt_match.group(1).replace(',', ''))
        
        # Check if we have enough for metrics
        has_purpose = bool(self.state.captured_context.purpose)
        has_income = bool(self.state.captured_context.monthly_income)
        has_employment = bool(self.state.captured_context.employment_type)
        has_amount = bool(self.state.captured_context.loan_amount or self.state.captured_context.property_value)
        
        if has_purpose and has_income and has_employment and has_amount:
            self.state.stage = ConversationStage.READY_FOR_METRICS
            return self._compute_and_present_metrics()
        else:
            # Ask for missing information
            missing = []
            if not has_employment:
                missing.append("Are you salaried, self-employed, or a contractor?")
            if not has_income:
                missing.append("What is your monthly income before deductions?")
            if not has_amount:
                if self.state.captured_context.purpose == "home_purchase":
                    missing.append("What's the property value and how much do you have for down payment?")
                else:
                    missing.append("How much are you looking to borrow?")
            
            response = "\n\n".join(missing)
            return self._build_response(response)
    
    def _handle_metrics_computation(self, message: str) -> Dict[str, Any]:
        """Stage 3: Compute and present loan snapshot + recommendations"""
        return self._compute_and_present_metrics()
    
    def _compute_and_present_metrics(self) -> Dict[str, Any]:
        """Compute loan metrics and present snapshot with recommendations"""
        ctx = self.state.captured_context
        
        # Compute loan amount if not set
        if ctx.property_value and ctx.down_payment:
            ctx.loan_amount = ctx.property_value - ctx.down_payment
        elif not ctx.loan_amount:
            ctx.loan_amount = ctx.property_value or 0
        
        # Default values
        loan_amount = ctx.loan_amount or 0
        property_value = ctx.property_value or loan_amount
        down_payment = ctx.down_payment or (property_value - loan_amount)
        income = ctx.monthly_income or 0
        tenure = ctx.loan_tenure_years or 15
        
        # Compute EMI (simplified formula)
        annual_rate = 0.065  # 6.5% base rate
        monthly_rate = annual_rate / 12
        num_payments = tenure * 12
        
        if monthly_rate > 0 and num_payments > 0:
            emi = loan_amount * monthly_rate * (1 + monthly_rate) ** num_payments / ((1 + monthly_rate) ** num_payments - 1)
        else:
            emi = loan_amount / num_payments
        
        total_repayment = emi * num_payments
        total_interest = total_repayment - loan_amount
        ltv = (loan_amount / property_value * 100) if property_value > 0 else 0
        foir = ((emi + (ctx.existing_debts or 0)) / income * 100) if income > 0 else 0
        
        # Create loan snapshot
        self.state.loan_snapshot = LoanSnapshot(
            loan_amount=loan_amount,
            down_payment=down_payment,
            property_value=property_value,
            estimated_emi=round(emi, 2),
            tenure_years=tenure,
            interest_rate=annual_rate * 100,
            total_interest=round(total_interest, 2),
            total_repayment=round(total_repayment, 2),
            ltv_ratio=round(ltv, 2),
            foir_ratio=round(foir, 2),
            currency=ctx.down_payment_currency or "USD"
        )
        
        # Create 3 recommendations
        self.state.recommendations = [
            LoanRecommendation(
                name="Aggressive Path",
                type="aggressive",
                interest_rate=5.9,
                tenure_years=10,
                monthly_emi=round(loan_amount * 0.0114, 2),
                total_interest=round(loan_amount * 0.37, 2),
                total_repayment=round(loan_amount * 1.37, 2),
                pros=["Lowest total interest", "Fastest debt-free", "Best long-term savings"],
                cons=["Highest monthly payment", "Less cash flow flexibility"],
                recommended=False
            ),
            LoanRecommendation(
                name="Balanced Path",
                type="balanced",
                interest_rate=6.5,
                tenure_years=15,
                monthly_emi=round(emi, 2),
                total_interest=round(total_interest, 2),
                total_repayment=round(total_repayment, 2),
                pros=["Moderate monthly payment", "Good interest savings", "Flexible cash flow"],
                cons=["Higher total interest than 10-year"],
                recommended=True
            ),
            LoanRecommendation(
                name="Conservative Path",
                type="conservative",
                interest_rate=7.2,
                tenure_years=20,
                monthly_emi=round(loan_amount * 0.0078, 2),
                total_interest=round(loan_amount * 0.87, 2),
                total_repayment=round(loan_amount * 1.87, 2),
                pros=["Lowest monthly payment", "Maximum cash flow", "Easiest qualification"],
                cons=["Highest total interest", "Longest debt period"],
                recommended=False
            )
        ]
        
        self.state.stage = ConversationStage.READY_FOR_RECOMMENDATION
        
        # Build response with XML tags for UI
        response = (
            f"<loan_snapshot>\n"
            f"Based on your profile, here's what we're looking at:\n\n"
            f"• Loan Amount: ${loan_amount:,.0f}\n"
            f"• Down Payment: ${down_payment:,.0f}\n"
            f"• Property Value: ${property_value:,.0f}\n"
            f"• Estimated EMI: ${emi:,.2f}/month\n"
            f"• Tenure: {tenure} years\n"
            f"• Interest Rate: ~{annual_rate*100:.1f}%\n"
            f"• Total Interest: ${total_interest:,.2f}\n"
            f"• LTV: {ltv:.1f}%\n"
            f"• FOIR: {foir:.1f}%\n"
            f"</loan_snapshot>\n\n"
            f"I've prepared three borrowing paths for you. Which would you prefer?\n\n"
            f"1. <loan_recommendation type='aggressive'>Aggressive Path</loan_recommendation> - Lower total interest, higher monthly payment\n"
            f"2. <loan_recommendation type='balanced'>Balanced Path</loan_recommendation> - Moderate payment, good savings\n"
            f"3. <loan_recommendation type='conservative'>Conservative Path</loan_recommendation> - Lowest payment, higher total cost"
        )
        
        return self._build_response(response, show_snapshot=True, show_recommendations=True)
    
    def _handle_recommendation_selection(self, message: str) -> Dict[str, Any]:
        """Stage 4: Handle recommendation selection"""
        message_lower = message.lower()
        
        # Determine selected option
        if any(word in message_lower for word in ["aggressive", "10-year", "10 year", "first", "option 1"]):
            self.state.selected_recommendation = self.state.recommendations[0]
        elif any(word in message_lower for word in ["balanced", "15-year", "15 year", "second", "option 2", "like", "prefer"]):
            self.state.selected_recommendation = self.state.recommendations[1]
        elif any(word in message_lower for word in ["conservative", "20-year", "20 year", "third", "option 3", "lower monthly"]):
            self.state.selected_recommendation = self.state.recommendations[2]
        
        if self.state.selected_recommendation:
            self.state.stage = ConversationStage.APPLICANT_IDENTITY
            response = (
                f"Excellent choice! The {self.state.selected_recommendation.name} suits your profile well.\n\n"
                f"To move forward with this option, I'll need your contact information:\n\n"
                f"1. Your email address\n"
                f"2. Your phone number\n\n"
                f"This will help us keep you updated on your application progress."
            )
        else:
            response = (
                "Could you let me know which option you prefer?\n\n"
                "1. Aggressive Path (10 years, lowest total interest)\n"
                "2. Balanced Path (15 years, moderate payment)\n"
                "3. Conservative Path (20 years, lowest monthly payment)"
            )
        
        return self._build_response(response)
    
    def _handle_applicant_identity(self, message: str) -> Dict[str, Any]:
        """Stage 5: Capture contact information"""
        message_lower = message.lower()
        
        # Extract email
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
        if email_match:
            self.state.captured_context.email = email_match.group(1)
        
        # Extract phone
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})', message)
        if phone_match:
            self.state.captured_context.phone = phone_match.group(1)
        
        # Check if we have both
        if self.state.captured_context.email and self.state.captured_context.phone:
            return self._submit_application()
        elif self.state.captured_context.email and not self.state.captured_context.phone:
            response = "Got your email! Now, what's your phone number?"
        elif self.state.captured_context.phone and not self.state.captured_context.email:
            response = "Got your phone number! Now, what's your email address?"
        else:
            response = (
                "To proceed with your loan application, I need:\n\n"
                "1. Your email address\n"
                "2. Your phone number"
            )
        
        return self._build_response(response)
    
    def _submit_application(self) -> Dict[str, Any]:
        """Submit application and trigger STP processing"""
        self.state.stage = ConversationStage.APPLICATION_SUBMITTED
        self.state.application_id = f"APP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create documents checklist
        employment = self.state.captured_context.employment_type
        purpose = self.state.captured_context.purpose
        
        self.state.documents_checklist = DocumentsChecklist(
            identity=[
                {"name": "National ID or Passport", "status": "required", "description": "Government-issued photo ID"},
                {"name": "Proof of Address", "status": "required", "description": "Utility bill or bank statement (last 3 months)"}
            ],
            income=[
                {"name": "Job Letter", "status": "required", "description": "Employment confirmation letter"},
                {"name": "Pay Slips", "status": "required", "description": "Last 3 months' pay slips"},
                {"name": "Bank Statements", "status": "required", "description": "Last 6 months' bank statements"},
                {"name": "NIS Record", "status": "optional", "description": "Social security contribution record"}
            ] if employment == "salaried" else [
                {"name": "Business Registration", "status": "required", "description": "Certificate of incorporation or business license"},
                {"name": "Financial Statements", "status": "required", "description": "Last 2 years' audited financial statements"},
                {"name": "Tax Returns", "status": "required", "description": "Last 2 years' tax returns"},
                {"name": "Bank Statements", "status": "required", "description": "Last 6 months' business bank statements"}
            ],
            property=[
                {"name": "Sale Agreement", "status": "required", "description": "Signed purchase agreement"},
                {"name": "Property Valuation Report", "status": "required", "description": "Professional valuation report"},
                {"name": "Title Deed", "status": "required", "description": "Property title documentation"},
                {"name": "Surveyor's Report", "status": "required", "description": "Land survey report"},
                {"name": "Down Payment Proof", "status": "required", "description": "Evidence of down payment funds"}
            ] if purpose == "home_purchase" else []
        )
        
        # Start STP processing
        self.state.stage = ConversationStage.STP_PROCESSING
        self.state.stp_checkpoints = [
            STPCheckpoint(name="Identity Verification", status="processing"),
            STPCheckpoint(name="AML/KYC Check", status="pending"),
            STPCheckpoint(name="Fraud Detection", status="pending"),
            STPCheckpoint(name="Credit Bureau Pull", status="pending"),
            STPCheckpoint(name="Affordability Assessment", status="pending"),
            STPCheckpoint(name="FOIR Validation", status="pending"),
            STPCheckpoint(name="LTV Assessment", status="pending"),
            STPCheckpoint(name="Employment Verification", status="pending"),
            STPCheckpoint(name="Income Validation", status="pending"),
            STPCheckpoint(name="Document Verification", status="pending"),
        ]
        
        identity_lines = [
            f"• {doc['name']} - {doc['description']}"
            for doc in self.state.documents_checklist.identity
        ]
        income_lines = [
            f"• {doc['name']} - {doc['description']}"
            for doc in self.state.documents_checklist.income
        ]
        identity_text = "\n".join(identity_lines)
        income_text = "\n".join(income_lines)
        
        response = (
            f"<loan_application id='{self.state.application_id}'>\n"
            f"Application Submitted Successfully!\n\n"
            f"Thank you, {self.state.captured_context.email}! Your application has been submitted.\n\n"
            f"Application ID: {self.state.application_id}\n"
            f"Loan Amount: ${self.state.loan_snapshot.loan_amount:,.0f}\n"
            f"Selected Option: {self.state.selected_recommendation.name}\n"
            f"</loan_application>\n\n"
            f"<documents_checklist>\n"
            f"Here are the documents we'll need from you:\n\n"
            f"**Identity Documents:**\n"
            f"{identity_text}\n\n"
            f"**Income Documents:**\n"
            f"{income_text}\n"
            f"</documents_checklist>\n\n"
            f"I'm now processing your application through our automated underwriting system. This will take just a moment..."
        )
        
        return self._build_response(
            response,
            show_documents=True,
            start_stp=True
        )
    
    def _handle_stp_processing(self, message: str) -> Dict[str, Any]:
        """Stage 6: Process STP checkpoints sequentially"""
        # Simulate STP processing
        if not self.state.stp_checkpoints or all(cp.status == "passed" for cp in self.state.stp_checkpoints):
            self.state.stp_completed = True
            self.state.stp_approved = True
            self.state.bureau_score = 720  # Simulated score
            self.state.stage = ConversationStage.TERMS_ACCEPTANCE
            self.state.awaiting_acceptance = True
            
            response = (
                f"<stp_completed>\n"
                f"Great news! Your application has been approved!\n\n"
                f"Credit Score: {self.state.bureau_score} (Good)\n"
                f"Approval Decision: APPROVED\n"
                f"</stp_completed>\n\n"
                f"<terms_acceptance>\n"
                f"Here are your final loan terms:\n\n"
                f"• Loan Amount: ${self.state.loan_snapshot.loan_amount:,.0f}\n"
                f"• Interest Rate: {self.state.selected_recommendation.interest_rate:.2f}%\n"
                f"• Tenure: {self.state.selected_recommendation.tenure_years} years\n"
                f"• Monthly EMI: ${self.state.selected_recommendation.monthly_emi:,.2f}\n"
                f"• Total Interest: ${self.state.selected_recommendation.total_interest:,.2f}\n"
                f"• Total Repayment: ${self.state.selected_recommendation.total_repayment:,.2f}\n\n"
                f"Please review the terms and provide your electronic signature to proceed with disbursement.\n"
                f"</terms_acceptance>"
            )
            
            return self._build_response(
                response,
                stp_completed=True,
                stp_approved=True,
                show_terms=True
            )
        
        # Process next checkpoint
        for checkpoint in self.state.stp_checkpoints:
            if checkpoint.status == "pending":
                checkpoint.status = "processing"
                response = f"Processing: {checkpoint.name}..."
                return self._build_response(response, stp_in_progress=True)
            elif checkpoint.status == "processing":
                checkpoint.status = "passed"
        
        # Continue processing
        return self._handle_stp_processing(message)
    
    def _handle_terms_acceptance(self, message: str) -> Dict[str, Any]:
        """Stage 7: Handle signature and terms acceptance"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["accept", "agree", "sign", "confirm", "yes", "proceed"]):
            self.state.terms_accepted = True
            self.state.stage = ConversationStage.DISBURSEMENT
            
            response = (
                f"<terms_accepted>\n"
                f"Terms Accepted! Thank you for your electronic signature.\n\n"
                f"Your loan is now being processed for disbursement...\n"
                f"</terms_accepted>"
            )
            
            return self._build_response(response, terms_accepted=True)
        else:
            response = (
                "To proceed, please confirm that you accept the loan terms by typing 'I accept' or clicking the signature button above."
            )
            return self._build_response(response)
    
    def _handle_disbursement(self, message: str) -> Dict[str, Any]:
        """Stage 8: Confirm disbursement"""
        self.state.disbursement_completed = True
        self.state.stage = ConversationStage.COMPLETED
        
        response = (
            f"<disbursement_completed>\n"
            f"🎉 Congratulations! Your loan has been disbursed!\n\n"
            f"Amount Credited: ${self.state.loan_snapshot.loan_amount:,.0f}\n"
            f"Transaction Reference: TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}\n"
            f"Account: ****{self.state.captured_context.phone[-4:] if self.state.captured_context.phone else '1234'}\n\n"
            f"Your first EMI of ${self.state.selected_recommendation.monthly_emi:,.2f} is due on {datetime.now().strftime('%B %d, %Y')}.\n\n"
            f"Thank you for choosing us for your lending needs!\n"
            f"</disbursement_completed>"
        )
        
        return self._build_response(
            response,
            disbursement_completed=True,
            show_celebration=True
        )
    
    def _handle_completed(self, message: str) -> Dict[str, Any]:
        """Final stage: Application completed"""
        response = (
            f"Your loan is active! Application ID: {self.state.application_id}\n\n"
            f"If you have any questions about your loan, feel free to ask. You can also:\n"
            f"• View your amortization schedule\n"
            f"• Make early payments\n"
            f"• Request loan statements\n"
            f"• Apply for additional products"
        )
        return self._build_response(response)
    
    def _build_response(
        self,
        response: str,
        show_snapshot: bool = False,
        show_recommendations: bool = False,
        show_documents: bool = False,
        start_stp: bool = False,
        stp_in_progress: bool = False,
        stp_completed: bool = False,
        stp_approved: bool = False,
        show_terms: bool = False,
        terms_accepted: bool = False,
        disbursement_completed: bool = False,
        show_celebration: bool = False
    ) -> Dict[str, Any]:
        """Build response with metadata for UI cards"""
        metadata = {
            "stage": self.state.stage.value,
            "conversationHistory": self.conversation_history.copy(),
        }
        
        if show_snapshot and self.state.loan_snapshot:
            metadata["loanSnapshot"] = self.state.loan_snapshot.model_dump()
        
        if show_recommendations and self.state.recommendations:
            metadata["loanRecommendations"] = [r.model_dump() for r in self.state.recommendations]
        
        if show_documents and self.state.documents_checklist:
            metadata["documentsChecklist"] = self.state.documents_checklist.model_dump()
        
        if start_stp or stp_in_progress or stp_completed:
            metadata["stpCheckpoints"] = [cp.model_dump() for cp in self.state.stp_checkpoints]
            metadata["stpInProgress"] = stp_in_progress
            metadata["stpCompleted"] = stp_completed
        
        if stp_approved:
            metadata["stpApproved"] = True
            metadata["bureauScore"] = self.state.bureau_score
        
        if show_terms:
            metadata["awaitingAcceptance"] = True
            metadata["loanApplication"] = {
                "id": self.state.application_id,
                "amount": self.state.loan_snapshot.loan_amount if self.state.loan_snapshot else 0,
                "rate": self.state.selected_recommendation.interest_rate if self.state.selected_recommendation else 0,
                "tenure": self.state.selected_recommendation.tenure_years if self.state.selected_recommendation else 0,
                "emi": self.state.selected_recommendation.monthly_emi if self.state.selected_recommendation else 0,
            }
        
        if terms_accepted:
            metadata["termsAccepted"] = True
        
        if disbursement_completed or show_celebration:
            metadata["disbursementCompleted"] = True
            metadata["celebration"] = True
        
        # Add loan application state for UI
        metadata["loanApplication"] = {
            "id": self.state.application_id,
            "stage": self.state.stage.value,
            "stpApproved": self.state.stp_approved,
            "stpCompleted": self.state.stp_completed,
            "awaitingAcceptance": self.state.awaiting_acceptance,
            "termsAccepted": self.state.terms_accepted,
            "disbursement": self.state.disbursement_completed,
        }
        
        return {
            "response": response,
            "metadata": metadata,
            "stage": self.state.stage.value,
        }


# Singleton instance
orchestrator_instances: Dict[str, LNAIOrchestrator] = {}

def get_orchestrator(session_id: str) -> LNAIOrchestrator:
    """Get or create orchestrator for session"""
    if session_id not in orchestrator_instances:
        orchestrator_instances[session_id] = LNAIOrchestrator()
    return orchestrator_instances[session_id]
