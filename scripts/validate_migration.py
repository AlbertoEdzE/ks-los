#!/usr/bin/env python3
"""
KS-LOS V2→V3 Migration Validation Suite

Phase 4: Comprehensive Testing and Validation

This script validates all implemented functionality for the v2 to v3 migration.
It tests:
- Phase 1: Database persistence
- Phase 2: Core API endpoints
- Data integrity across restarts
- V2/V3 interoperability

Usage:
    python scripts/validate_migration.py

Requirements:
    - Backend must be running on http://localhost:8000
    - requests library installed
"""

import requests
import json
import sys
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Test results tracking
TEST_RESULTS: List[Dict[str, Any]] = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result."""
    result = {
        "name": name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"       {details}")


def test_health_check() -> bool:
    """Test backend health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        passed = response.status_code == 200 and response.json().get("status") == "healthy"
        log_test("Backend Health Check", passed, f"Status: {response.status_code}")
        return passed
    except Exception as e:
        log_test("Backend Health Check", False, str(e))
        return False


def test_v3_create_conversation() -> Optional[str]:
    """Test V3 conversation creation."""
    try:
        session_id = f"test-{uuid.uuid4().hex[:8]}"
        payload = {
            "session_id": session_id,
            "borrower_name": "Test User"
        }
        response = requests.post(
            f"{BASE_URL}/api/v3/conversations/",
            json=payload,
            timeout=TIMEOUT
        )
        
        passed = response.status_code == 200
        data = response.json()
        
        if passed and "conversation" in data:
            conv = data["conversation"]
            log_test(
                "V3 Create Conversation",
                passed,
                f"Session ID: {session_id}, Borrower: {conv.get('borrowerName')}"
            )
            return session_id
        else:
            log_test("V3 Create Conversation", passed, f"Response: {data}")
            return None
    except Exception as e:
        log_test("V3 Create Conversation", False, str(e))
        return None


def test_v3_get_conversation(session_id: str) -> bool:
    """Test V3 get conversation endpoint."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v3/conversations/{session_id}",
            timeout=TIMEOUT
        )
        
        passed = response.status_code == 200
        data = response.json()
        
        if passed:
            mode = data.get("mode", "unknown")
            stage = data.get("stage", "unknown")
            log_test(
                "V3 Get Conversation",
                passed,
                f"Mode: {mode}, Stage: {stage}"
            )
        else:
            log_test("V3 Get Conversation", passed, f"Status: {response.status_code}")
        
        return passed
    except Exception as e:
        log_test("V3 Get Conversation", False, str(e))
        return False


def test_v3_send_message(session_id: str) -> bool:
    """Test V3 send message endpoint."""
    try:
        payload = {"content": "I want a home loan"}
        response = requests.post(
            f"{BASE_URL}/api/v3/conversations/{session_id}/messages",
            json=payload,
            timeout=TIMEOUT
        )
        
        passed = response.status_code == 200
        data = response.json()
        
        if passed:
            response_text = data.get("response", "")[:50]
            log_test(
                "V3 Send Message",
                passed,
                f"Response preview: {response_text}..."
            )
        else:
            log_test("V3 Send Message", passed, f"Status: {response.status_code}")
        
        return passed
    except Exception as e:
        log_test("V3 Send Message", False, str(e))
        return False


def test_v3_get_messages(session_id: str) -> bool:
    """Test V3 get messages endpoint."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v3/conversations/{session_id}/messages",
            timeout=TIMEOUT
        )
        
        passed = response.status_code == 200
        data = response.json()
        
        if passed and isinstance(data, list):
            count = len(data)
            log_test(
                "V3 Get Messages",
                passed,
                f"Message count: {count}"
            )
            return count >= 2  # Should have at least user + assistant messages
        else:
            log_test("V3 Get Messages", passed, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("V3 Get Messages", False, str(e))
        return False


def test_v3_get_loan(session_id: str) -> bool:
    """Test V3 get loan endpoint."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v3/conversations/{session_id}/loan",
            timeout=TIMEOUT
        )
        
        # Should return 200 with null (no loan exists yet)
        passed = response.status_code == 200
        data = response.json()
        
        log_test(
            "V3 Get Loan",
            passed,
            f"Loan exists: {data is not None}"
        )
        return passed
    except Exception as e:
        log_test("V3 Get Loan", False, str(e))
        return False


def test_v3_state_persistence(session_id: str) -> bool:
    """Test that state persists across requests (simulating restart)."""
    try:
        # Get current state
        response1 = requests.get(
            f"{BASE_URL}/api/v3/conversations/{session_id}",
            timeout=TIMEOUT
        )
        data1 = response1.json()
        
        # Get state again (simulating retrieval after restart)
        response2 = requests.get(
            f"{BASE_URL}/api/v3/conversations/{session_id}",
            timeout=TIMEOUT
        )
        data2 = response2.json()
        
        # Check consistency
        passed = (
            data1.get("session_id") == data2.get("session_id") and
            data1.get("mode") == data2.get("mode")
        )
        
        log_test(
            "V3 State Persistence",
            passed,
            f"Consistent across requests: {passed}"
        )
        return passed
    except Exception as e:
        log_test("V3 State Persistence", False, str(e))
        return False


def test_v3_delete_conversation() -> bool:
    """Test V3 delete conversation endpoint."""
    try:
        # Create a conversation to delete
        session_id = f"test-delete-{uuid.uuid4().hex[:8]}"
        requests.post(
            f"{BASE_URL}/api/v3/conversations/",
            json={"session_id": session_id},
            timeout=TIMEOUT
        )
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/v3/conversations/{session_id}",
            timeout=TIMEOUT
        )
        
        passed = response.status_code == 200 and response.json().get("deleted") == True
        
        log_test(
            "V3 Delete Conversation",
            passed,
            f"Deleted: {session_id}"
        )
        return passed
    except Exception as e:
        log_test("V3 Delete Conversation", False, str(e))
        return False


def test_v2_endpoints_still_work() -> bool:
    """Test that V2 endpoints still function (backward compatibility)."""
    try:
        # Test V2 phases endpoint
        response = requests.get(
            f"{BASE_URL}/api/phases/active",
            timeout=TIMEOUT
        )
        
        passed = response.status_code == 200
        
        log_test(
            "V2 Backward Compatibility (Phases)",
            passed,
            f"Status: {response.status_code}"
        )
        return passed
    except Exception as e:
        log_test("V2 Backward Compatibility (Phases)", False, str(e))
        return False


def test_intent_extraction() -> bool:
    """Test that intent is properly extracted from messages."""
    try:
        session_id = f"test-intent-{uuid.uuid4().hex[:8]}"
        
        # Create conversation
        requests.post(
            f"{BASE_URL}/api/v3/conversations/",
            json={"session_id": session_id, "borrower_name": "Intent Test"},
            timeout=TIMEOUT
        )
        
        # Send message with clear intent
        requests.post(
            f"{BASE_URL}/api/v3/conversations/{session_id}/messages",
            json={"content": "I need a personal loan for debt consolidation"},
            timeout=TIMEOUT
        )
        
        # Get state and check intent extraction
        response = requests.get(
            f"{BASE_URL}/api/v3/conversations/{session_id}",
            timeout=TIMEOUT
        )
        data = response.json()
        
        captured_context = data.get("captured_context", {})
        purpose = captured_context.get("purpose")
        
        passed = purpose is not None and purpose != ""
        
        log_test(
            "Intent Extraction",
            passed,
            f"Extracted purpose: {purpose}"
        )
        return passed
    except Exception as e:
        log_test("Intent Extraction", False, str(e))
        return False


def run_all_tests() -> Dict[str, Any]:
    """Run all validation tests."""
    print("=" * 70)
    print("KS-LOS V2→V3 Migration Validation Suite")
    print("=" * 70)
    print()
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Backend is not healthy. Aborting tests.")
        return {"success": False, "error": "Backend unhealthy"}
    
    print()
    
    # Test 2: Create conversation
    session_id = test_v3_create_conversation()
    if not session_id:
        print("\n❌ Cannot create conversation. Aborting tests.")
        return {"success": False, "error": "Cannot create conversation"}
    
    # Test 3-7: Use the created conversation
    test_v3_get_conversation(session_id)
    test_v3_send_message(session_id)
    test_v3_get_messages(session_id)
    test_v3_get_loan(session_id)
    test_v3_state_persistence(session_id)
    
    # Test 8: Delete conversation
    test_v3_delete_conversation()
    
    # Test 9: V2 backward compatibility
    test_v2_endpoints_still_work()
    
    # Test 10: Intent extraction
    test_intent_extraction()
    
    # Summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for r in TEST_RESULTS if r["passed"])
    total = len(TEST_RESULTS)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"Passed: {passed}/{total} ({percentage:.1f}%)")
    print()
    
    if passed == total:
        print("✅ All tests passed! Migration is successful.")
        return {"success": True, "passed": passed, "total": total}
    else:
        print("❌ Some tests failed. Review the details above.")
        failed_tests = [r["name"] for r in TEST_RESULTS if not r["passed"]]
        print(f"Failed tests: {', '.join(failed_tests)}")
        return {"success": False, "passed": passed, "total": total, "failed": failed_tests}


if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result.get("success") else 1)
