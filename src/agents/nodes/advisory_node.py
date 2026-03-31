"""
Advisory Node for Agentic Orchestrator

Implements Mode 1 of the LNAI conversation flow: Understanding & Estimation.

Conversation Flow (Mode 1 - Advisory):
    Step 1: Understand the need (purpose, borrower name)
    Step 2: Employment & income capture
    Step 3: Financial details (loan amount, existing debts)
    Step 4: Loan snapshot + 3 recommendations (COMBINED output)

This node uses LLM for natural language understanding while maintaining
deterministic calculation engines for financial metrics.

Usage:
    node = AdvisoryNode()
    updated_state = node.process(current_state)
"""

from typing import Dict, List, Any, Optional
import logging
import re

from langchain_core.messages import HumanMessage, AIMessage

from src.agents.graph_state import AgenticOrchestratorState, ConversationMode, Message
from src.agents.prompts import BORROWER_SYSTEM_PROMPT, RESPONSE_GENERATION_PROMPT
from src.agents.structured_parser import parse_llm_response, IntentAnalysis
from src.agents.agent_tools.intent_extractor import IntentExtractorTool
from src.agents.response_generator import (
    XMLTagResponseGenerator,
    IntentCaptureStrategy,
    FinancialContextStrategy,
    RecommendationStrategy,
)
from src.core.calculation_engines import (
    compute_reducing_emi,
    compute_affordability,
    compute_credit_risk,
    compute_collateral_metrics,
    compute_file_completeness,
)


class AdvisoryNode:
    """
    Handles Mode 1 (Advisory) of borrower conversation.
    
    Responsibilities:
    1. Extract borrower intent using LLM
    2. Collect financial context progressively
    3. Compute loan metrics using deterministic engines
    4. Generate recommendations from product catalog
    5. Present snapshot + recommendations together
    
    Scientific Design:
    - LLM for natural language understanding (flexible)
    - Deterministic calculations for financial metrics (precise)
    - Confidence-based progression (robust)
    - One intent per turn (user-friendly)
    
    Usage:
        node = AdvisoryNode(llm=chat_model, product_catalog=catalog)
        state = node.process(state)
    """
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        product_catalog: Optional[List[Dict]] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize advisory node.
        
        Args:
            llm: LLM model for conversation (ChatOllama, ChatOpenAI, etc.)
            product_catalog: List of available loan products
            config: Configuration options
        """
        self.llm = llm
        self.product_catalog = product_catalog or []
        self.config = config or {}
        
        self.intent_extractor = IntentExtractorTool()
        self.response_generator = XMLTagResponseGenerator()
        
        self.logger = logging.getLogger(__name__)
    
    def _to_float(self, value: Any) -> float:
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                return float(value.replace(",", "").replace("$", "").strip())
        except Exception:
            pass
        return 0.0
    
    def process(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Process advisory mode conversation.
        
        Args:
            state: Current agentic state
            
        Returns:
            Updated state with new responses and extracted context
        """
        self.logger.info(f"Processing advisory mode, stage: {state.current_stage}")

        if state.recommendations and state.selected_recommendation is None:
            if self._try_capture_recommendation_selection(state):
                state.update_timestamp()
                return state

        step = self._determine_step(state)
        
        # Execute appropriate step
        if step == "understand_need":
            state = self._step1_understand_need(state)
        
        elif step == "employment_income":
            state = self._step2_employment_income(state)
        
        elif step == "financial_details":
            state = self._step3_financial_details(state)
        
        elif step == "snapshot_and_recommendations":
            state = self._step4_snapshot_and_recommendations(state)

        elif step == "await_selection":
            state = self._step4b_await_selection(state)
        
        state.update_timestamp()
        return state

    def _try_capture_recommendation_selection(self, state: AgenticOrchestratorState) -> bool:
        last_user_text = None
        for m in reversed(state.conversation_history):
            if m.role == "user":
                last_user_text = m.content
                break
        if not last_user_text:
            return False

        text = last_user_text.strip().lower()
        if not text:
            return False

        for rec in state.recommendations:
            name = (rec.name or "").strip().lower()
            typ = (rec.type or "").strip().lower()
            if (name and name in text) or (typ and typ in text):
                state.selected_recommendation = rec
                state.mode = ConversationMode.APPLICATION
                state.current_stage = "contact_capture"
                state.add_message(
                    "assistant",
                    f"Great — we'll go with the {rec.name} option. What’s your email address and phone number so I can proceed with your application?",
                    metadata={"selected_recommendation": rec.model_dump()},
                )
                return True

        return False
    
    def _determine_step(self, state: AgenticOrchestratorState) -> str:
        """
        Determine current advisory step based on captured context.
        
        Returns:
            Step name: understand_need, employment_income, financial_details,
                      or snapshot_and_recommendations
        """
        context = state.captured_context
        
        if context.purpose and context.borrower_name and context.employment_type and context.monthly_income and context.loan_amount and context.existing_debts is not None:
            if not state.loan_snapshot or not state.recommendations:
                return "snapshot_and_recommendations"
            if state.selected_recommendation is None:
                return "await_selection"
            return "snapshot_and_recommendations"
        
        # Step 3: Have employment/income, need loan amount
        if context.employment_type and context.monthly_income:
            return "financial_details"
        
        # Step 2: Have purpose, need employment/income
        if context.purpose and context.borrower_name:
            return "employment_income"
        
        # Step 1: Need to understand purpose
        return "understand_need"

    def _step4b_await_selection(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        state.add_message(
            "assistant",
            "Which option would you like to go with — Fast Track, Balanced, or Comfort?",
            metadata={"awaiting_recommendation_selection": True},
        )
        return state
    
    def _step1_understand_need(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Step 1: Understand borrower's need.
        
        Scientific Design (per LNAI specification):
        - Extracts: Loan purpose (home, auto, personal, etc.)
        - Extracts: Borrower name (CRITICAL - must be captured in Step 1)
        - Extracts: Initial context (urgency, timeline, etc.)
        
        Agentic Intelligence:
        - LLM extracts both purpose AND name from conversation
        - If name is missing, agent INTELLIGENTLY prompts for it
        - The HOW is natural (LLM-generated), but the GOAL is fixed
        - ONE INTENT PER TURN: Don't ask for name AND purpose together
        
        Flow Logic:
        1. First turn: Greet and ask about loan purpose (don't overwhelm)
        2. Subsequent turns: Extract purpose AND name via LLM
        3. If purpose captured but name missing: Intelligently ask for name
        4. If both captured: Proceed to Step 2 (Employment & income)
        """
        # Get last user message
        if not state.conversation_history:
            # Initial greeting - ask about purpose only (don't overwhelm user)
            response_text = (
                "Hello! I'm your Loan Navigator. I'm here to help you find the most "
                "efficient path to the funding you need. To get us started, could you "
                "tell me a bit about what you're looking to achieve? Are you thinking "
                "about a new home, a car, starting a business, or perhaps a personal loan?"
            )

            state.add_message("assistant", response_text)
            return state

        # Extract intent from conversation using LLM
        last_message = state.conversation_history[-1].content

        try:
            # Use LLM to extract intent (purpose + name + other fields)
            conv_history = [
                {"role": m.role, "content": m.content}
                for m in state.conversation_history
            ]
            extraction = self.intent_extractor._run(conversation_history=conv_history)

            # Parse extraction result
            from src.agents.agent_tools.intent_extractor import IntentExtractionResult
            result = IntentExtractionResult.model_validate_json(extraction)

            # Update context with extracted data
            if result.context.purpose:
                state.captured_context.purpose = result.context.purpose
            if result.context.borrower_name:
                state.captured_context.borrower_name = result.context.borrower_name

            # Store confidence scores
            state.confidence_scores.update(result.field_confidence)

            self.logger.info(
                f"Extracted intent: purpose={state.captured_context.purpose}, "
                f"name={state.captured_context.borrower_name}, "
                f"confidence={result.confidence:.2f}"
            )

        except Exception as e:
            self.logger.warning(f"Intent extraction failed: {str(e)}")
            # Continue with fallback

        # Generate response using LLM-based strategy
        # The strategy INTELLIGENTLY decides what to ask based on what's missing
        strategy = IntentCaptureStrategy()
        has_purpose = bool(state.captured_context.purpose)
        has_name = bool(state.captured_context.borrower_name)

        # CRITICAL: If we have purpose but NOT name, we MUST ask for name
        # This is per LNAI design - Step 1 requires BOTH purpose AND name
        response_text = strategy.generate(
            context=state.captured_context,
            stage=None,  # Not used in strategy
            has_purpose=has_purpose,
            has_name=has_name,  # NEW: Pass name status for intelligent prompting
        )

        state.add_message("assistant", response_text)

        return state
    
    def _step2_employment_income(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Step 2: Capture employment type and income.
        
        Extracts:
        - Employment type (salaried, self-employed, contractor)
        - Monthly income (before deductions)
        - Business details (if self-employed)
        """
        # Get last user message
        if not state.conversation_history:
            return state
        
        # Extract employment and income using LLM
        try:
            extraction = self.intent_extractor._run(
                conversation_history=[
                    {"role": m.role, "content": m.content}
                    for m in state.conversation_history
                ]
            )
            
            from src.agents.agent_tools.intent_extractor import IntentExtractionResult
            result = IntentExtractionResult.model_validate_json(extraction)
            
            # Update context
            if result.context.employment_type:
                state.captured_context.employment_type = result.context.employment_type
            if result.context.monthly_income:
                state.captured_context.monthly_income = result.context.monthly_income
            
            # Update confidence scores
            state.confidence_scores.update(result.field_confidence)
            
        except Exception as e:
            self.logger.warning(f"Employment/income extraction failed: {str(e)}")
        
        # Generate response
        strategy = FinancialContextStrategy()
        has_employment = bool(state.captured_context.employment_type)
        has_income = bool(state.captured_context.monthly_income)
        
        response_text = strategy.generate(
            context=state.captured_context,
            stage=None,
            has_income=has_income,
            has_employment=has_employment,
        )
        
        state.add_message("assistant", response_text)
        
        return state
    
    def _step3_financial_details(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Step 3: Capture loan amount and existing debts.
        
        Extracts:
        - Loan amount needed
        - Existing debts/obligations
        - Property value (for home loans)
        - Down payment (if applicable)
        """
        # Get last user message
        if not state.conversation_history:
            return state
        
        last_user_text = state.conversation_history[-1].content

        # Extract financial details using LLM
        try:
            extraction = self.intent_extractor._run(
                conversation_history=[
                    {"role": m.role, "content": m.content}
                    for m in state.conversation_history
                ]
            )
            
            from src.agents.agent_tools.intent_extractor import IntentExtractionResult
            result = IntentExtractionResult.model_validate_json(extraction)
            
            # Update context
            if result.context.loan_amount:
                state.captured_context.loan_amount = result.context.loan_amount
            if result.context.existing_debts is not None:
                state.captured_context.existing_debts = result.context.existing_debts
            
            # Update confidence scores
            state.confidence_scores.update(result.field_confidence)
            
        except Exception as e:
            self.logger.warning(f"Financial details extraction failed: {str(e)}")
        
        if state.captured_context.existing_debts is None:
            lowered = last_user_text.strip().lower()
            if lowered in {"none", "no", "nil", "n/a", "na", "0"}:
                state.captured_context.existing_debts = 0.0
                state.captured_context.has_existing_debts = False
            elif re.search(r"\b(no|none|nil|zero)\b", lowered) and not re.search(r"\d", lowered):
                state.captured_context.existing_debts = 0.0
                state.captured_context.has_existing_debts = False

        # Check if we have enough for snapshot
        context = state.captured_context
        has_amount = bool(context.loan_amount)
        has_debts = context.existing_debts is not None
        
        if has_amount and has_debts and bool(context.borrower_name):
            # Ready for snapshot + recommendations
            return self._step4_snapshot_and_recommendations(state)

        if not bool(context.borrower_name):
            state.add_message("assistant", "Before I calculate options, what’s your full name (first and last)?")
            return state

        if not has_amount:
            state.add_message(
                "assistant",
                "Thanks — roughly how much are you looking to borrow (and the currency, e.g. USD 50,000)?",
            )
            return state

        state.add_message(
            "assistant",
            "And do you have any current monthly loan repayments, credit cards, or other commitments? If none, just say 'none'.",
        )
        
        return state
    
    
    def _step3b_contact_capture(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Step 3b: Capture contact information (email, phone).
        
        This step comes after financial details but before showing recommendations.
        We need contact info to proceed with application.
        """
        # Get last user message
        if not state.conversation_history:
            return state
        
        last_message = state.conversation_history[-1].content
        
        # Extract contact info using LLM
        try:
            conv_history = [
                {"role": m.role, "content": m.content}
                for m in state.conversation_history
            ]
            extraction = self.intent_extractor._run(conversation_history=conv_history)
            
            from src.agents.agent_tools.intent_extractor import IntentExtractionResult
            result = IntentExtractionResult.model_validate_json(extraction)
            
            # Update context
            if result.context.email:
                state.captured_context.email = result.context.email
            if result.context.phone:
                state.captured_context.phone = result.context.phone
            
            # Update confidence scores
            state.confidence_scores.update(result.field_confidence)
            
        except Exception as e:
            self.logger.warning(f"Contact extraction failed: {str(e)}")
        
        # Check if we have contact info
        context = state.captured_context
        has_email = bool(context.email)
        has_phone = bool(context.phone)
        
        if has_email and has_phone:
            # Have contact info, proceed to recommendations
            return self._step4_snapshot_and_recommendations(state)
        else:
            # Ask for missing contact info
            missing = []
            if not has_email:
                missing.append("email address")
            if not has_phone:
                missing.append("phone number")
            
            response_text = (
                f"Great! Now I just need your {', '.join(missing)} so I can keep you updated on your application. "
                f"{'What is your email address?' if not has_email else ''}"
                f"{' And what is your phone number?' if not has_phone else ''}"
            )
            
            state.add_message("assistant", response_text)
        
        return state

    def _step4_snapshot_and_recommendations(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Step 4: Compute loan snapshot and present 3 recommendations.
        
        This is the CRITICAL step where we:
        1. Compute deterministic loan metrics (EMI, FOIR, LTV)
        2. Generate 3 recommendation options from product catalog
        3. Present BOTH snapshot and recommendations together
        
        IMPORTANT: Never show snapshot without recommendations!
        """
        context = state.captured_context
        
        # Validate we have required data
        if not all([
            context.purpose,
            context.loan_amount,
            context.monthly_income,
            context.employment_type
        ]):
            self.logger.error("Missing required data for snapshot")
            return state
        
        # ──────────────────────────────────────────────────────────────────
        # Compute Loan Metrics (Deterministic - NO LLM)
        # ──────────────────────────────────────────────────────────────────
        
        loan_amount = self._to_float(context.loan_amount)
        monthly_income = self._to_float(context.monthly_income)
        existing_debts = self._to_float(context.existing_debts)
        
        # Compute EMI for different tenure options
        base_rate = 0.085  # 8.5% base rate
        tenures = [15, 20, 25]  # years

        emi_results = []
        for tenure in tenures:
            emi_result = compute_reducing_emi(
                principal=loan_amount,
                annual_rate=base_rate * 100,
                tenure_months=tenure * 12
            )
            emi_results.append({
                "tenure": tenure,
                "emi": emi_result.emi,  # Fixed: was monthly_payment
                "total_interest": emi_result.total_interest,
                "total_repayment": emi_result.total_repayment,
            })
        
        # Compute affordability metrics
        affordability = compute_affordability(
            monthly_income=monthly_income,
            existing_emi_total=existing_debts,
            proposed_emi=emi_results[1]["emi"]  # Middle option
        )
        
        # Compute collateral metrics (if any)
        property_value = float(context.property_value) if isinstance(context.property_value, (int, float)) else 0.0
        down_payment = float(context.down_payment) if isinstance(context.down_payment, (int, float)) else 0.0
        has_collateral = property_value > 0.0
        collateral = compute_collateral_metrics(
            loan_amount=loan_amount,
            collateral_value=property_value,
            haircut_percent=15.0,
            security_type="property" if has_collateral else "none",
            down_payment=down_payment
        )
        
        # Compute completeness score from available context
        loan_data = {
            "borrower_name": context.borrower_name,
            "loan_type": (context.purpose or "").strip() or "personal",
            "loan_amount": loan_amount,
            "purpose": context.purpose,
            "employment_type": context.employment_type,
            "monthly_income": monthly_income,
            "existing_debts": existing_debts,
            "credit_score": context.credit_score or None,
            "collateral": "yes" if has_collateral else "no",
            "down_payment": down_payment,
            "property_value": property_value,
        }
        completeness_score = compute_file_completeness(loan_data)
        credit_score = context.credit_score if isinstance(context.credit_score, int) else 650
        loan_type = (context.purpose or "").strip() or "personal"
        
        # Compute credit risk
        credit_risk = compute_credit_risk(
            affordability=affordability,
            collateral=collateral,
            credit_score=credit_score,
            completeness_score=completeness_score,
            loan_type=loan_type,
            has_collateral=has_collateral,
        )
        
        # Create loan snapshot
        from src.agents.graph_state import LoanSnapshot
        
        state.loan_snapshot = LoanSnapshot(
            loan_amount=loan_amount,
            down_payment=0,  # Will be populated if provided
            property_value=loan_amount,  # Default for non-home loans
            estimated_emi=emi_results[1]["emi"],
            tenure_years=20,
            interest_rate=base_rate * 100,
            total_interest=emi_results[1]["total_interest"],
            total_repayment=emi_results[1]["total_repayment"],
            ltv_ratio=100.0,  # Will be updated for home loans
            foir_ratio=affordability.foir if hasattr(affordability, 'foir') else None,
        )
        
        # ──────────────────────────────────────────────────────────────────
        # Generate Recommendations (from product catalog or default)
        # ──────────────────────────────────────────────────────────────────
        
        from src.agents.graph_state import LoanRecommendation
        
        state.recommendations = [
            LoanRecommendation(
                name="Fast Track",
                type="aggressive",
                interest_rate=7.5,
                tenure_years=15,
                monthly_emi=emi_results[0]["emi"],
                total_interest=emi_results[0]["total_interest"],
                total_repayment=emi_results[0]["total_repayment"],
                pros=["Lowest total interest", "Fastest debt-free"],
                cons=["Highest monthly payment"],
                recommended=False,
            ),
            LoanRecommendation(
                name="Balanced",
                type="balanced",
                interest_rate=8.5,
                tenure_years=20,
                monthly_emi=emi_results[1]["emi"],
                total_interest=emi_results[1]["total_interest"],
                total_repayment=emi_results[1]["total_repayment"],
                pros=["Manageable payments", "Good balance"],
                cons=["Moderate total interest"],
                recommended=True,  # Default recommendation
            ),
            LoanRecommendation(
                name="Comfort",
                type="conservative",
                interest_rate=9.5,
                tenure_years=25,
                monthly_emi=emi_results[2]["emi"],
                total_interest=emi_results[2]["total_interest"],
                total_repayment=emi_results[2]["total_repayment"],
                pros=["Lowest monthly payment", "Most flexibility"],
                cons=["Highest total interest"],
                recommended=False,
            ),
        ]
        
        # ──────────────────────────────────────────────────────────────────
        # Generate Response with XML Tags
        # ──────────────────────────────────────────────────────────────────
        
        strategy = RecommendationStrategy()
        response_text = strategy.generate(
            context=context,
            stage=None,
            snapshot=state.loan_snapshot,
            recommendations=state.recommendations,
        )
        
        state.add_message("assistant", response_text, metadata={
            "loan_snapshot": state.loan_snapshot.model_dump(),
            "recommendations": [r.model_dump() for r in state.recommendations],
            "affordability": affordability.model_dump() if hasattr(affordability, 'model_dump') else {},
        })
        
        self.logger.info(
            f"Generated snapshot + recommendations: "
            f"EMI=${emi_results[1]['emi']:,.2f}, FOIR={affordability.foir:.1%}"
        )
        
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_advisory(state: AgenticOrchestratorState, **kwargs) -> AgenticOrchestratorState:
    """
    Convenience function to process advisory mode.
    
    Args:
        state: Current state
        **kwargs: Additional arguments for node initialization
        
    Returns:
        Updated state
    """
    node = AdvisoryNode(**kwargs)
    return node.process(state)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "AdvisoryNode",
    "process_advisory",
]
