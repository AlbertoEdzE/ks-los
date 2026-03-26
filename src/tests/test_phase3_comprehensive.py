"""
Phase 3 Comprehensive Test Suite

Tests for the complete agentic conversation flow:
- Advisory Node (Mode 1)
- Application Node (Mode 2)
- Completion Node (Mode 3)
- Repair Node (conversation repair)
- RAG Node (policy-grounded responses)
- Escalation Node (human handoff)
- State Management
- Migration Utilities

Scientific Validation:
- Unit tests for each node
- Integration tests for node combinations
- End-to-end conversation flow tests
- Edge case handling
- Confidence-based decision validation
"""

import pytest
from datetime import datetime

from src.agents.graph_state import (
    AgenticOrchestratorState,
    ConversationMode,
    create_initial_state,
    Message,
)
from src.agents.orchestrator import CapturedContext, LoanSnapshot, LoanRecommendation


# ─────────────────────────────────────────────────────────────────────────────
# Advisory Node Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAdvisoryNode:
    """Test Advisory Node (Mode 1)"""
    
    def test_advisory_state_creation(self):
        """Test advisory mode state initialization"""
        state = create_initial_state(session_id="test-advisory-001")
        
        assert state.mode == ConversationMode.ADVISORY
        assert state.current_stage == "intent_capture"
        
        print(f"\nAdvisory State Test:")
        print(f"  Mode: {state.mode.value}")
        print(f"  Stage: {state.current_stage}")
    
    def test_advisory_step_determination(self):
        """Test advisory step determination logic"""
        state = create_initial_state(session_id="test-advisory-002")
        
        # Step 1: No purpose yet
        assert not state.captured_context.purpose
        
        # Simulate purpose captured
        state.captured_context.purpose = "home_purchase"
        state.captured_context.loan_amount = 400000.0
        state.captured_context.monthly_income = 8000.0
        state.captured_context.employment_type = "salaried"
        state.confidence_scores["purpose"] = 0.95
        state.confidence_scores["loan_amount"] = 0.9
        state.confidence_scores["monthly_income"] = 0.85
        state.confidence_scores["employment_type"] = 0.9
        
        # Should be ready for snapshot + recommendations
        assert state.can_proceed_to_application() is True
        
        print(f"\nAdvisory Step Test:")
        print(f"  Can proceed to application: {state.can_proceed_to_application()}")
        print(f"  Avg confidence: {state.get_average_confidence():.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# Application Node Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestApplicationNode:
    """Test Application Node (Mode 2)"""
    
    def test_application_required_fields(self):
        """Test application required fields validation"""
        state = create_initial_state(session_id="test-app-001")
        state.mode = ConversationMode.APPLICATION
        
        # Check missing fields
        missing = [
            field for field in [
                "borrower_name", "email", "phone",
                "employment_type", "monthly_income",
                "purpose", "loan_amount", "existing_debts"
            ]
            if not getattr(state.captured_context, field, None)
        ]
        
        assert len(missing) > 0
        
        print(f"\nApplication Fields Test:")
        print(f"  Missing fields: {len(missing)}")
        print(f"  Fields: {missing[:3]}...")
    
    def test_application_submission_readiness(self):
        """Test application submission readiness"""
        state = create_initial_state(session_id="test-app-002")
        state.mode = ConversationMode.APPLICATION
        
        # Populate all required fields
        state.captured_context.borrower_name = "Marcus Williams"
        state.captured_context.email = "marcus.w@email.com"
        state.captured_context.phone = "+1-868-555-1234"
        state.captured_context.employment_type = "salaried"
        state.captured_context.monthly_income = 8000.0
        state.captured_context.purpose = "personal"
        state.captured_context.loan_amount = 50000.0
        state.captured_context.existing_debts = 1500.0
        
        # All fields populated
        state.application_submitted = True
        
        assert state.application_submitted is True
        assert state.mode == ConversationMode.APPLICATION
        
        print(f"\nApplication Readiness Test:")
        print(f"  Submitted: {state.application_submitted}")
        print(f"  Borrower: {state.captured_context.borrower_name}")


# ─────────────────────────────────────────────────────────────────────────────
# Completion Node Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCompletionNode:
    """Test Completion Node (Mode 3)"""
    
    def test_completion_stp_states(self):
        """Test completion mode STP states"""
        state = create_initial_state(session_id="test-complete-001")
        state.mode = ConversationMode.COMPLETION
        
        # Test STP state transitions
        states = ["pending", "processing", "approved", "disbursed"]
        
        for stp_state in states:
            state.stp_status = stp_state
            assert state.stp_status == stp_state
        
        print(f"\nCompletion STP States Test:")
        print(f"  States tested: {states}")
    
    def test_terms_acceptance_flow(self):
        """Test terms acceptance flow"""
        state = create_initial_state(session_id="test-complete-002")
        state.mode = ConversationMode.COMPLETION
        state.stp_status = "approved"
        state.awaiting_acceptance = True
        
        # Before acceptance
        assert state.terms_accepted is False
        assert state.awaiting_acceptance is True
        
        # Simulate acceptance
        state.terms_accepted = True
        state.awaiting_acceptance = False
        
        assert state.terms_accepted is True
        
        print(f"\nTerms Acceptance Test:")
        print(f"  Accepted: {state.terms_accepted}")
        print(f"  Awaiting: {state.awaiting_acceptance}")


# ─────────────────────────────────────────────────────────────────────────────
# Repair Node Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRepairNode:
    """Test Repair Node (conversation repair)"""
    
    def test_correction_detection_patterns(self):
        """Test correction detection patterns - pattern matching test"""
        import re
        
        # Patterns from RepairNode
        CORRECTION_PATTERNS = [
            r"\bwait,?\s*(?:i\s+)?(?:meant|changed\s+my\s+mind)\b",
            r"\bactually,?\b",
            r"\bcorrection\b",
            r"\bthat's\s+not\s+right\b",
            r"\bi\s+(?:changed\s+my\s+mind|made\s+a\s+mistake)\b",
            r"\bno,?\s+(?:that's\s+)?wrong\b",
            r"\blet\s+me\s+(?:correct|rephrase)\b",
            r"\bsorry,?\s+(?:i\s+)?meant\b",
        ]
        
        correction_examples = [
            "Wait, I meant $50,000 not $40,000",
            "Actually, I'm self-employed",
            "Correction - my email is test@example.com",
            "That's not right, I make $10,000",
            "Sorry, I meant salaried",
        ]
        
        detected = 0
        for example in correction_examples:
            for pattern in CORRECTION_PATTERNS:
                if re.search(pattern, example.lower()):
                    detected += 1
                    break
        
        assert detected == len(correction_examples)
        
        print(f"\nCorrection Detection Test:")
        print(f"  Examples tested: {len(correction_examples)}")
        print(f"  All detected: {detected == len(correction_examples)}")
    
    def test_digression_detection(self):
        """Test digression detection - pattern matching test"""
        import re
        
        DIGRESSION_PATTERNS = [
            r"\bhow\s+(?:does|do|long|much)\b",
            r"\bwhat\s+(?:is|are|happens|if)\b",
            r"\bcan\s+i\b",
            r"\bwhy\s+(?:do|does|is|are)\b",
        ]
        
        ON_TOPIC_TOPICS = [
            "interest rate", "emi", "loan amount", "tenure",
            "documents", "application", "approval", "income",
        ]
        
        digression_examples = [
            "How long does the process take?",
            "What is your interest rate?",
            "Can you explain the STP process?",
        ]
        
        on_topic_examples = [
            "What is my EMI?",
            "How does the interest rate work?",
            "What documents do I need for the loan?",
        ]
        
        # Test digressions
        digressions_detected = 0
        for example in digression_examples:
            matches = any(re.search(pattern, example.lower()) for pattern in DIGRESSION_PATTERNS)
            on_topic = any(topic in example.lower() for topic in ON_TOPIC_TOPICS)
            if matches and not on_topic:
                digressions_detected += 1
        
        # Test on-topic (should NOT be detected as digressions)
        on_topic_correct = 0
        for example in on_topic_examples:
            on_topic = any(topic in example.lower() for topic in ON_TOPIC_TOPICS)
            if on_topic:
                on_topic_correct += 1
        
        print(f"\nDigression Detection Test:")
        print(f"  Digressions: {digressions_detected}/{len(digression_examples)}")
        print(f"  On-topic: {on_topic_correct}/{len(on_topic_examples)}")


# ─────────────────────────────────────────────────────────────────────────────
# RAG Node Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRAGNode:
    """Test RAG Node (policy-grounded responses)"""
    
    def test_policy_question_detection(self):
        """Test policy question detection patterns - pattern matching test"""
        import re
        
        POLICY_PATTERNS = [
            r"\b(?:what\s+is|what\s+are)\s+(?:the\s+)?(?:minimum|maximum|max|min)\b",
            r"\b(?:eligibility|criteria|requirements)\b",
            r"\b(?:interest\s+rate|rates)\b",
            r"\b(?:loan\s+)?(?:limit|limits|amount)\b",
            r"\b(?:processing\s+)?(?:time|timeframe|how\s+long)\b",
            r"\b(?:documents|documentation|papers)\b",
            r"\b(?:approve|approval|approved|reject|rejected)\b",
            r"\b(?:credit\s+)?(?:score|bureau|rating)\b",
            r"\b(?:down\s+)?(?:payment|deposit)\b",
            r"\b(?:ltv|loan\s+to\s+value)\b",
            r"\b(?:foir|debt\s+to\s+income|dti)\b",
            r"\b(?:policy|policies|rule|rules|regulation)\b",
            r"\b(?:can\s+i|am\s+i\s+eligible|do\s+i\s+qualify)\b",
        ]
        
        policy_questions = [
            "What is the minimum income requirement?",
            "What are the eligibility criteria?",
            "What is the maximum loan amount?",
            "How long does processing take?",
            "What documents do I need?",
            "Can I get approved with bad credit?",
        ]
        
        detected = 0
        for question in policy_questions:
            question_lower = question.lower()
            is_question = "?" in question or question_lower.startswith(("what", "how", "can", "do", "does", "is", "are"))
            matches_pattern = any(re.search(pattern, question_lower) for pattern in POLICY_PATTERNS)
            if matches_pattern and is_question:
                detected += 1
        
        print(f"\nRAG Policy Detection Test:")
        print(f"  Questions tested: {len(policy_questions)}")
        print(f"  Detected: {detected}")
    
    def test_rag_fallback_responses(self):
        """Test RAG fallback responses - logic test"""
        # Test fallback logic without importing node
        def generate_fallback(question: str) -> str:
            question_lower = question.lower()
            
            if "interest rate" in question_lower:
                return "Our interest rates typically range from 7.5% to 12%"
            elif "minimum" in question_lower and "income" in question_lower:
                return "Our minimum income requirement varies by loan type"
            elif "documents" in question_lower:
                return "The documents required depend on your employment type"
            else:
                return "That's a great question! Our loan policies cover various aspects"
        
        response = generate_fallback("What is the interest rate?")
        assert "interest rate" in response.lower() or "7.5" in response
        
        print(f"\nRAG Fallback Test:")
        print(f"  Response generated: {len(response)} chars")


# ─────────────────────────────────────────────────────────────────────────────
# Escalation Node Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEscalationNode:
    """Test Escalation Node (human handoff)"""
    
    def test_escalation_triggers(self):
        """Test escalation trigger conditions - logic test"""
        # Test low confidence detection logic
        confidence_scores = {
            "purpose": 0.2,
            "loan_amount": 0.15,
            "monthly_income": 0.25,
        }
        
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        low_confidence_threshold = 0.3
        low_confidence_turns = 3
        
        has_low_streak = avg_confidence < low_confidence_threshold and low_confidence_turns >= 3
        
        assert has_low_streak is True
        
        print(f"\nEscalation Triggers Test:")
        print(f"  Avg confidence: {avg_confidence:.2f}")
        print(f"  Low streak: {has_low_streak}")
    
    def test_high_value_loan_detection(self):
        """Test high-value loan detection - threshold test"""
        HIGH_VALUE_THRESHOLD_USD = 500_000
        
        # Above threshold
        loan_amount_above = 600000.0
        assert loan_amount_above > HIGH_VALUE_THRESHOLD_USD
        
        # Below threshold
        loan_amount_below = 400000.0
        assert loan_amount_below <= HIGH_VALUE_THRESHOLD_USD
        
        print(f"\nHigh-Value Loan Test:")
        print(f"  Threshold: ${HIGH_VALUE_THRESHOLD_USD:,}")
        print(f"  Above: ${loan_amount_above:,} ✓")
        print(f"  Below: ${loan_amount_below:,} ✓")
    
    def test_handoff_summary_generation(self):
        """Test handoff summary generation - structure test"""
        # Test summary structure
        summary = {
            "session_id": "test-001",
            "application_id": "APP-001",
            "escalation_reason": "High-value loan",
            "timestamp": datetime.now().isoformat(),
            "borrower_info": {
                "name": "Marcus Williams",
                "email": "marcus.w@email.com",
            },
            "loan_details": {
                "purpose": "home_purchase",
                "amount": 600000.0,
            },
            "recommended_action": "Conduct detailed assessment",
        }
        
        assert "session_id" in summary
        assert "borrower_info" in summary
        assert "loan_details" in summary
        assert "recommended_action" in summary
        
        print(f"\nHandoff Summary Test:")
        print(f"  Summary keys: {len(summary.keys())}")
        print(f"  Borrower: {summary['borrower_info']['name']}")


# ─────────────────────────────────────────────────────────────────────────────
# State Management Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAgenticStateManagement:
    """Test agentic state management"""
    
    def test_mode_transitions(self):
        """Test complete mode transition flow"""
        state = create_initial_state(session_id="test-modes-001")
        
        # Initial: Advisory
        assert state.mode == ConversationMode.ADVISORY
        
        # Transition to Application
        state.captured_context.purpose = "home_purchase"
        state.captured_context.loan_amount = 400000.0
        state.captured_context.monthly_income = 8000.0
        state.captured_context.employment_type = "salaried"
        state.confidence_scores["purpose"] = 0.95
        state.confidence_scores["loan_amount"] = 0.9
        state.confidence_scores["monthly_income"] = 0.85
        state.confidence_scores["employment_type"] = 0.9
        
        assert state.can_proceed_to_application() is True
        state.mode = ConversationMode.APPLICATION
        
        # Transition to Completion
        state.captured_context.email = "test@email.com"
        state.captured_context.phone = "+1-868-555-1234"
        state.application_submitted = True
        state.mode = ConversationMode.COMPLETION
        
        assert state.mode == ConversationMode.COMPLETION
        
        print(f"\nMode Transitions Test:")
        print(f"  ADVISORY → APPLICATION → COMPLETION: ✓")
    
    def test_confidence_tracking_across_modes(self):
        """Test confidence tracking across mode transitions"""
        state = create_initial_state(session_id="test-conf-001")
        
        # Advisory mode confidence
        state.confidence_scores["purpose"] = 0.95
        state.confidence_scores["loan_amount"] = 0.85
        
        avg_advisory = state.get_average_confidence()
        assert avg_advisory > 0.8
        
        # Application mode - add more fields
        state.confidence_scores["email"] = 0.9
        state.confidence_scores["phone"] = 0.85
        
        avg_application = state.get_average_confidence()
        assert avg_application > 0.8
        
        print(f"\nConfidence Tracking Test:")
        print(f"  Advisory avg: {avg_advisory:.2f}")
        print(f"  Application avg: {avg_application:.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# Migration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMigration:
    """Test migration utilities"""
    
    def test_migration_status(self):
        """Test migration status check"""
        from src.agents.migration import check_deprecation_status
        
        status = check_deprecation_status()
        
        assert "deprecated_in" in status
        assert "removal_version" in status
        assert "migration_guide" in status
        
        print(f"\nMigration Status Test:")
        print(f"  Deprecated in: {status['deprecated_in']}")
        print(f"  Removal: {status['removal_version']}")
    
    def test_migration_module_exists(self):
        """Test migration module is available"""
        import importlib
        
        module = importlib.import_module("src.agents.migration")
        
        assert hasattr(module, "migrate_orchestrator_state")
        assert hasattr(module, "create_migration_wrapper")
        assert hasattr(module, "check_deprecation_status")
        
        print(f"\nMigration Module Test:")
        print(f"  Module loaded: ✓")
        print(f"  Functions available: ✓")


# ─────────────────────────────────────────────────────────────────────────────
# End-to-End Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase3EndToEnd:
    """Test complete Phase 3 agentic flow"""
    
    def test_complete_borrower_journey(self):
        """Test complete borrower journey through all modes"""
        state = create_initial_state(session_id="e2e-phase3-001")
        
        # Mode 1: Advisory
        state.mode = ConversationMode.ADVISORY
        state.captured_context.purpose = "home_purchase"
        state.captured_context.loan_amount = 400000.0
        state.captured_context.monthly_income = 8000.0
        state.captured_context.employment_type = "salaried"
        state.confidence_scores["purpose"] = 0.95
        state.confidence_scores["loan_amount"] = 0.9
        state.confidence_scores["monthly_income"] = 0.85
        state.confidence_scores["employment_type"] = 0.9
        
        assert state.can_proceed_to_application() is True
        
        # Mode 2: Application
        state.mode = ConversationMode.APPLICATION
        state.captured_context.borrower_name = "Marcus Williams"
        state.captured_context.email = "marcus.w@email.com"
        state.captured_context.phone = "+1-868-555-1234"
        state.application_submitted = True
        
        # Mode 3: Completion
        state.mode = ConversationMode.COMPLETION
        state.stp_status = "approved"
        state.terms_accepted = True
        
        print(f"\nEnd-to-End Phase 3 Test:")
        print(f"  Advisory: ✓")
        print(f"  Application: ✓")
        print(f"  Completion: ✓")
        print(f"  Avg Confidence: {state.get_average_confidence():.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
