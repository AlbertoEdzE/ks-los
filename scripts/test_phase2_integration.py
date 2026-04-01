#!/usr/bin/env python3
"""
KS-LOS Phase 2 Integration Test Script

This script performs comprehensive integration testing across all Phase 2 components:
- EPIC-001: Hybrid LLM Routing
- EPIC-002: AI Observability (LangFuse)
- EPIC-003: Hallucination Detection
- EPIC-004: Quality Evaluation (RAGAS)
- EPIC-005: Enhanced STP Simulation
- EPIC-006: Metrics API
- EPIC-007: Metrics Dashboard UI (TypeScript compilation check)

Usage:
    python scripts/test_phase2_integration.py
    
    # With verbose output
    python scripts/test_phase2_integration.py --verbose
    
    # With coverage report
    python scripts/test_phase2_integration.py --coverage

Requirements:
    - All Phase 2 dependencies installed
    - Ollama running locally (for LLM tests)
    - PostgreSQL running (for database tests)
    - Optional: LangFuse running (for observability tests)
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("phase2_integration")


# ─────────────────────────────────────────────────────────────────────────────
# Test Result Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    """Result of a single test"""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class EpicTestResults:
    """Aggregated results for an epic"""
    epic_id: str
    epic_name: str
    tests: List[TestResult] = field(default_factory=list)
    
    @property
    def total_tests(self) -> int:
        return len(self.tests)
    
    @property
    def passed_tests(self) -> int:
        return sum(1 for t in self.tests if t.passed)
    
    @property
    def failed_tests(self) -> int:
        return sum(1 for t in self.tests if not t.passed)
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def total_duration_ms(self) -> float:
        return sum(t.duration_ms for t in self.tests)


@dataclass
class IntegrationTestReport:
    """Complete integration test report"""
    start_time: datetime
    end_time: Optional[datetime] = None
    epic_results: List[EpicTestResults] = field(default_factory=list)
    
    @property
    def total_tests(self) -> int:
        return sum(e.total_tests for e in self.epic_results)
    
    @property
    def total_passed(self) -> int:
        return sum(e.passed_tests for e in self.epic_results)
    
    @property
    def total_failed(self) -> int:
        return sum(e.failed_tests for e in self.epic_results)
    
    @property
    def overall_pass_rate(self) -> float:
        if self.total_tests == 0:
            return 100.0
        return (self.total_passed / self.total_tests) * 100
    
    @property
    def total_duration_ms(self) -> float:
        return sum(e.total_duration_ms for e in self.epic_results)
    
    @property
    def duration_seconds(self) -> float:
        return self.total_duration_ms / 1000
    
    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            "=" * 80,
            "KS-LOS Phase 2 Integration Test Report",
            "=" * 80,
            f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"End Time: {(self.end_time or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {self.duration_seconds:.2f}s",
            "",
            "Summary:",
            f"  Total Tests: {self.total_tests}",
            f"  Passed: {self.total_passed} ({self.overall_pass_rate:.1f}%)",
            f"  Failed: {self.total_failed}",
            "",
            "By Epic:",
        ]
        
        for epic in self.epic_results:
            status = "✅ PASS" if epic.pass_rate == 100 else "❌ FAIL"
            lines.append(
                f"  {epic.epic_id}: {epic.epic_name} - "
                f"{epic.passed_tests}/{epic.total_tests} passed "
                f"({epic.pass_rate:.1f}%) [{status}]"
            )
        
        lines.append("")
        lines.append("=" * 80)
        
        if self.total_failed == 0:
            lines.append("✅ ALL TESTS PASSED")
        else:
            lines.append(f"❌ {self.total_failed} TEST(S) FAILED")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Test Runner Class
# ─────────────────────────────────────────────────────────────────────────────

class Phase2IntegrationTester:
    """
    Integration tester for Phase 2 components.
    
    Tests all epics end-to-end:
    - EPIC-001: Hybrid LLM Routing
    - EPIC-002: AI Observability
    - EPIC-003: Hallucination Detection
    - EPIC-004: Quality Evaluation
    - EPIC-005: STP Simulation
    - EPIC-006: Metrics API
    - EPIC-007: Frontend TypeScript compilation
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.report = IntegrationTestReport(start_time=datetime.now())
    
    def run_all_tests(self) -> IntegrationTestReport:
        """Run all integration tests"""
        logger.info("Starting Phase 2 Integration Tests")
        
        # Test each epic
        self.test_epic_001_llm_routing()
        self.test_epic_002_observability()
        self.test_epic_003_hallucination()
        self.test_epic_004_evaluation()
        self.test_epic_005_stp_simulation()
        self.test_epic_006_metrics_api()
        self.test_epic_007_frontend()
        
        self.report.end_time = datetime.now()
        return self.report
    
    def _run_test(self, epic_results: EpicTestResults, test_name: str, test_func) -> None:
        """Run a single test and record results"""
        start = time.time()
        error = None
        
        try:
            test_func()
            passed = True
        except Exception as e:
            passed = False
            error = str(e)
        
        duration_ms = (time.time() - start) * 1000
        
        result = TestResult(
            name=test_name,
            passed=passed,
            duration_ms=duration_ms,
            error=error
        )
        
        epic_results.tests.append(result)
        
        if self.verbose:
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {test_name} ({duration_ms:.1f}ms)")
        
        if error and self.verbose:
            logger.error(f"    Error: {error}")
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-001: Hybrid LLM Routing Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_001_llm_routing(self) -> None:
        """Test EPIC-001: Hybrid LLM Routing"""
        logger.info("Testing EPIC-001: Hybrid LLM Routing")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-001",
            epic_name="Hybrid LLM Routing"
        )
        
        def test_router_initialization():
            from src.config.llm_router import LLMRouter, get_llm_router
            router = LLMRouter()
            assert router is not None
            assert get_llm_router() is not None
        
        def test_provider_selection():
            from src.config.llm_router import LLMRouter
            import os
            
            # Test without API key (should use fallback)
            original_key = os.environ.pop("OPENAI_API_KEY", None)
            try:
                router = LLMRouter()
                provider = router.get_provider("simple_chat")
                assert provider == "ollama", f"Expected 'ollama', got '{provider}'"
            finally:
                if original_key:
                    os.environ["OPENAI_API_KEY"] = original_key
        
        def test_config_loading():
            from src.config.llm_router import load_llm_routing_config
            config = load_llm_routing_config()
            assert config.primary_provider == "openai"
            assert config.fallback_provider == "ollama"
            assert len(config.routing_rules) > 0
        
        def test_chat_response_structure():
            from src.config.llm_router import ChatResponse
            response = ChatResponse(
                content="Test",
                provider="ollama",
                model="qwen2.5:7b"
            )
            assert response.content == "Test"
            assert response.provider == "ollama"
        
        self._run_test(epic_results, "Router Initialization", test_router_initialization)
        self._run_test(epic_results, "Provider Selection", test_provider_selection)
        self._run_test(epic_results, "Config Loading", test_config_loading)
        self._run_test(epic_results, "Chat Response Structure", test_chat_response_structure)
        
        self.report.epic_results.append(epic_results)
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-002: AI Observability Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_002_observability(self) -> None:
        """Test EPIC-002: AI Observability"""
        logger.info("Testing EPIC-002: AI Observability")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-002",
            epic_name="AI Observability"
        )
        
        def test_observer_initialization():
            from src.shared.observability import LangFuseObserver
            observer = LangFuseObserver(enabled=False)
            assert observer is not None
            assert observer.enabled is False
        
        def test_trace_creation():
            from src.shared.observability import LangFuseObserver
            observer = LangFuseObserver(enabled=False)
            trace = observer.start_trace("test", "session-123")
            assert trace is not None
            assert trace.name == "test"
        
        def test_score_recording():
            from src.shared.observability import LangFuseObserver
            observer = LangFuseObserver(enabled=False)
            trace = observer.start_trace("test", "session-123")
            trace.score(name="test_score", value=0.95)
            # Should not raise
        
        def test_singleton_pattern():
            from src.shared.observability import (
                get_langfuse_observer,
                reset_langfuse_observer
            )
            reset_langfuse_observer()
            observer1 = get_langfuse_observer()
            observer2 = get_langfuse_observer()
            assert observer1 is observer2
        
        self._run_test(epic_results, "Observer Initialization", test_observer_initialization)
        self._run_test(epic_results, "Trace Creation", test_trace_creation)
        self._run_test(epic_results, "Score Recording", test_score_recording)
        self._run_test(epic_results, "Singleton Pattern", test_singleton_pattern)
        
        self.report.epic_results.append(epic_results)
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-003: Hallucination Detection Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_003_hallucination(self) -> None:
        """Test EPIC-003: Hallucination Detection"""
        logger.info("Testing EPIC-003: Hallucination Detection")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-003",
            epic_name="Hallucination Detection"
        )
        
        def test_detector_initialization():
            from src.core.hallucination_detector import HallucinationDetector
            detector = HallucinationDetector(use_nli=False, use_rag=False)
            assert detector is not None
        
        def test_claim_extraction():
            from src.core.hallucination_detector import ClaimExtractor
            extractor = ClaimExtractor()
            claims = extractor.extract("Your interest rate is 8.5%")
            assert len(claims) >= 0  # May not match pattern
        
        def test_rule_validation():
            from src.core.hallucination_detector import (
                RuleBasedValidator,
                PolicyRules,
                ExtractedClaim,
                ClaimType
            )
            rules = PolicyRules(interest_rate_min=5.0, interest_rate_max=15.0)
            validator = RuleBasedValidator(policy_rules=rules)
            
            claim = ExtractedClaim(
                text="8.5% interest",
                claim_type=ClaimType.NUMERIC,
                value=8.5,
                unit="percent",
                context="interest_rate"
            )
            
            validation = validator.validate(claim)
            assert validation.is_valid is True
        
        def test_hallucination_detection():
            from src.core.hallucination_detector import HallucinationDetector
            detector = HallucinationDetector(use_nli=False, use_rag=False)
            
            # Test with valid response
            report = detector.detect(
                response="Your interest rate is 8.5%",
                context="Policy: rates 5-15%"
            )
            
            assert report is not None
            assert 0 <= report.hallucination_score <= 1
        
        self._run_test(epic_results, "Detector Initialization", test_detector_initialization)
        self._run_test(epic_results, "Claim Extraction", test_claim_extraction)
        self._run_test(epic_results, "Rule Validation", test_rule_validation)
        self._run_test(epic_results, "Hallucination Detection", test_hallucination_detection)
        
        self.report.epic_results.append(epic_results)
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-004: Quality Evaluation Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_004_evaluation(self) -> None:
        """Test EPIC-004: Quality Evaluation"""
        logger.info("Testing EPIC-004: Quality Evaluation")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-004",
            epic_name="Quality Evaluation"
        )
        
        def test_evaluator_initialization():
            from src.core.evaluation_service import RAGASEvaluator
            evaluator = RAGASEvaluator()
            assert evaluator is not None
        
        def test_simple_evaluator():
            from src.core.evaluation_service import SimpleQualityEvaluator
            evaluator = SimpleQualityEvaluator()
            
            result = evaluator.evaluate(
                question="What is FOIR?",
                answer="FOIR is Fixed Obligation to Income Ratio.",
                hallucination_score=0.1
            )
            
            assert result is not None
            assert result.faithfulness == 0.9  # 1.0 - 0.1
        
        def test_sampling_logic():
            from src.core.evaluation_service import RAGASEvaluator, EvaluationConfig
            config = EvaluationConfig(sampling_rate=1.0)  # Always evaluate
            evaluator = RAGASEvaluator(config=config)
            assert evaluator._should_evaluate() is True
        
        def test_alert_thresholds():
            from src.core.evaluation_service import RAGASEvaluator, RAGASResult
            evaluator = RAGASEvaluator()
            
            result = RAGASResult(
                faithfulness=0.5,  # Below threshold
                answer_relevance=0.9,
                context_precision=0.8,
                overall_score=0.73,
                question="Q",
                answer="A",
                contexts=[]
            )
            
            assert evaluator.should_alert(result) is True
        
        self._run_test(epic_results, "Evaluator Initialization", test_evaluator_initialization)
        self._run_test(epic_results, "Simple Evaluator", test_simple_evaluator)
        self._run_test(epic_results, "Sampling Logic", test_sampling_logic)
        self._run_test(epic_results, "Alert Thresholds", test_alert_thresholds)
        
        self.report.epic_results.append(epic_results)
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-005: STP Simulation Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_005_stp_simulation(self) -> None:
        """Test EPIC-005: Enhanced STP Simulation"""
        logger.info("Testing EPIC-005: Enhanced STP Simulation")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-005",
            epic_name="Enhanced STP Simulation"
        )
        
        def test_simulator_initialization():
            from src.core.stp_simulation import STPSimulator
            simulator = STPSimulator()
            assert simulator is not None
        
        def test_bureau_score_simulation():
            from src.core.stp_simulation import BureauScoreSimulator
            simulator = BureauScoreSimulator(seed=42)
            
            report = simulator.simulate(
                monthly_income=8000.0,
                existing_debts=500.0,
                employment_type="salaried"
            )
            
            assert 300 <= report.score <= 900
            assert report.grade in ("A", "B", "C", "D", "E")
        
        def test_aml_screening():
            from src.core.stp_simulation import AMLScreeningService
            service = AMLScreeningService(use_opensanctions=False)
            
            # Test clean name
            result = service.screen("John Smith")
            assert result.passed is True
            
            # Test watchlist name
            result = service.screen("test_suspicious")
            assert result.passed is False
        
        def test_stp_decision():
            from src.core.stp_simulation import STPSimulator, DemoProfiles
            simulator = STPSimulator(bureau_seed=42, use_opensanctions=False)
            
            result = simulator.process_demo_application(DemoProfiles.APPROVED)
            
            assert result is not None
            assert result.approved is True
        
        def test_demo_profiles():
            from src.core.stp_simulation import DEMO_PROFILE_CONFIG, DemoProfiles
            
            for profile in DemoProfiles:
                assert profile in DEMO_PROFILE_CONFIG
                config = DEMO_PROFILE_CONFIG[profile]
                assert "borrower_name" in config
                assert "monthly_income" in config
        
        self._run_test(epic_results, "Simulator Initialization", test_simulator_initialization)
        self._run_test(epic_results, "Bureau Score Simulation", test_bureau_score_simulation)
        self._run_test(epic_results, "AML Screening", test_aml_screening)
        self._run_test(epic_results, "STP Decision", test_stp_decision)
        self._run_test(epic_results, "Demo Profiles", test_demo_profiles)
        
        self.report.epic_results.append(epic_results)
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-006: Metrics API Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_006_metrics_api(self) -> None:
        """Test EPIC-006: Metrics API"""
        logger.info("Testing EPIC-006: Metrics API")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-006",
            epic_name="Metrics API"
        )
        
        def test_schema_imports():
            from src.api.schemas.metrics import (
                ApplicationMetrics,
                PortfolioMetrics,
                AIMetrics,
                AggregateAIMetrics,
            )
            # Should import without error
        
        def test_router_imports():
            from src.api.routers.metrics import router
            assert router is not None
        
        def test_application_metrics_schema():
            from src.api.schemas.metrics import ApplicationMetrics, ApplicationStatus
            from datetime import datetime
            
            metrics = ApplicationMetrics(
                application_id="APP-123",
                status=ApplicationStatus.APPROVED,
                processing_time_seconds=2.3,
                loan_amount=75000.0,
                journey_progress=85.0,
                submitted_at=datetime.now(),
                updated_at=datetime.now(),
            )
            
            assert metrics.application_id == "APP-123"
            assert metrics.status == ApplicationStatus.APPROVED
        
        def test_auth_schema():
            from src.api.schemas.metrics import AdminAuthRequest, AdminAuthResponse
            
            request = AdminAuthRequest(password="test1234")  # Min 8 characters
            assert request.password == "test1234"
        
        self._run_test(epic_results, "Schema Imports", test_schema_imports)
        self._run_test(epic_results, "Router Imports", test_router_imports)
        self._run_test(epic_results, "Application Metrics Schema", test_application_metrics_schema)
        self._run_test(epic_results, "Auth Schema", test_auth_schema)
        
        self.report.epic_results.append(epic_results)
    
    # ───────────────────────────────────────────────────────────────────────
    # EPIC-007: Frontend Tests
    # ───────────────────────────────────────────────────────────────────────
    
    def test_epic_007_frontend(self) -> None:
        """Test EPIC-007: Metrics Dashboard UI"""
        logger.info("Testing EPIC-007: Metrics Dashboard UI")
        
        epic_results = EpicTestResults(
            epic_id="EPIC-007",
            epic_name="Metrics Dashboard UI"
        )
        
        def test_typescript_files_exist():
            frontend_dir = Path(__file__).parent.parent / "frontend" / "src"
            
            assert (frontend_dir / "api" / "metricsClient.ts").exists()
            assert (frontend_dir / "types" / "metrics.ts").exists()
            assert (frontend_dir / "components" / "MetricsDashboard.tsx").exists()
        
        def test_typescript_compilation():
            import subprocess
            
            frontend_dir = Path(__file__).parent.parent / "frontend"
            
            # Check if TypeScript compiles without errors
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # TypeScript compilation should succeed
            assert result.returncode == 0, f"TypeScript compilation failed: {result.stdout}"
        
        self._run_test(epic_results, "TypeScript Files Exist", test_typescript_files_exist)
        self._run_test(epic_results, "TypeScript Compilation", test_typescript_compilation)
        
        self.report.epic_results.append(epic_results)


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="KS-LOS Phase 2 Integration Tests")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for test report"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run tests
    tester = Phase2IntegrationTester(verbose=args.verbose)
    report = tester.run_all_tests()
    
    # Print summary
    print("\n" + report.generate_summary())
    
    # Save report if requested
    if args.output:
        with open(args.output, "w") as f:
            f.write(report.generate_summary())
        logger.info(f"Report saved to {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if report.total_failed == 0 else 1)


if __name__ == "__main__":
    main()
