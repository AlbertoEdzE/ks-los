# KS-LOS v2 → v3 Migration: Scientific Implementation Plan

**Document Type:** Research & Development Protocol  
**Version:** 1.0.0  
**Date:** March 26, 2026  
**Methodology:** Incremental Validation with Formal Verification Gates  
**Institutional Standard:** Oxford Engineering Rigor

---

## 🎯 Executive Summary

This document presents a **formally-verified migration protocol** for transitioning the KS-LOS system from v2 (deterministic workflow) to v3 (agentic workflow). Each phase includes:

1. **Formal specification** of expected behavior
2. **Invariant preservation** checks
3. **Empirical validation** through automated testing
4. **Rollback procedures** for safety

---

## 📐 Methodological Framework

### Design Principles

1. **Non-Regression:** No existing functionality shall be broken during migration
2. **Data Integrity:** All conversation state must be preserved across restarts
3. **Backward Compatibility:** v2 clients must continue functioning during migration
4. **Formal Verification:** Each component must pass specification tests
5. **Observability:** All state transitions must be auditable

### Validation Gate Structure

Each phase must pass three validation tiers:

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: Unit Correctness                                   │
│  - Individual component specification tests                 │
│  - Type safety verification                                 │
│  - Edge case coverage                                       │
├─────────────────────────────────────────────────────────────┤
│  Tier 2: Integration Correctness                            │
│  - Component interaction verification                       │
│  - API contract compliance                                  │
│  - Database transaction integrity                           │
├─────────────────────────────────────────────────────────────┤
│  Tier 3: System Correctness                                 │
│  - End-to-end workflow validation                           │
│  - Performance benchmarks                                   │
│  - Failure mode analysis                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Phase Chronology

### Phase 1: Database Foundation (Week 1)
**Objective:** Establish persistent state storage for v3 agentic state

**Rationale:** Without persistence, the system cannot be production-grade. This is the **foundational dependency** for all subsequent phases.

**Dependencies:** None (foundational)

**Deliverables:**
1.1. V3ConversationState database schema  
1.2. State persistence layer with ACID guarantees  
1.3. State reconstruction from database  
1.4. Migration utilities (v2 → v3 state mapping)

**Validation Gates:**
- ✅ State survives backend restart (persistence test)
- ✅ State can be queried via SQL (auditability test)
- ✅ Concurrent state updates are serialized correctly (isolation test)
- ✅ State reconstruction is lossless (integrity test)

---

### Phase 2: Core API Endpoints (Week 2)
**Objective:** Implement missing v3 endpoints required by frontend

**Rationale:** Frontend currently receives 404 errors for critical endpoints. This blocks user-facing functionality.

**Dependencies:** Phase 1 (database foundation)

**Deliverables:**
2.1. `GET /api/v3/conversations/{id}/loan` endpoint  
2.2. `GET /api/v3/conversations/{id}/messages` endpoint  
2.3. `GET /api/v3/conversations/{id}` endpoint (v2-compatible format)  
2.4. `POST /api/v3/conversations/{id}/loan` endpoint  
2.5. Error handling with proper HTTP semantics

**Validation Gates:**
- ✅ All endpoints return correct HTTP status codes
- ✅ Response schemas match frontend expectations
- ✅ Database queries are optimized (N+1 prevention)
- ✅ Error responses include correlation IDs

---

### Phase 3: Integration Layer (Week 3)
**Objective:** Create v2/v3 compatibility adapters

**Rationale:** Officer dashboard uses v2, borrower chat uses v3. Need seamless interoperability.

**Dependencies:** Phase 2 (core API)

**Deliverables:**
3.1. V2→V3 state adapter (for officer dashboard)  
3.2. V3→V2 response transformer (for frontend compatibility)  
3.3. Unified conversation listing (v2 + v3 merged)  
3.4. Cross-version referential integrity

**Validation Gates:**
- ✅ Officer dashboard can view v3 conversations
- ✅ Borrower chat can access v2 loans
- ✅ No data duplication across versions
- ✅ Version detection is automatic

---

### Phase 4: Validation Suite (Week 4)
**Objective:** Comprehensive automated testing

**Rationale:** Scientific rigor requires reproducible verification of all claims.

**Dependencies:** Phases 1-3 (functional system)

**Deliverables:**
4.1. Unit test suite (>90% coverage)  
4.2. Integration test suite (API contracts)  
4.3. End-to-end test suite (user workflows)  
4.4. Performance benchmark suite  
4.5. Chaos engineering tests (failure modes)

**Validation Gates:**
- ✅ All tests pass on CI/CD pipeline
- ✅ Code coverage >90%
- ✅ Performance within 10% of v2 baseline
- ✅ No memory leaks under sustained load

---

### Phase 5: Production Hardening (Week 5)
**Objective:** Prepare for production deployment

**Rationale:** Research prototype → production system requires additional rigor.

**Dependencies:** Phases 1-4 (validated system)

**Deliverables:**
5.1. Observability integration (metrics, tracing, alerts)  
5.2. Backup/recovery procedures  
5.3. Deployment runbooks  
5.4. Monitoring dashboards  
5.5. Incident response procedures

**Validation Gates:**
- ✅ Jaeger traces show complete request flow
- ✅ Prometheus metrics capture all KPIs
- ✅ Backup restoration tested successfully
- ✅ Alert thresholds configured appropriately

---

## 🔬 Detailed Implementation Protocol

### Phase 1: Database Foundation

#### 1.1 Schema Specification

```sql
-- Formal schema specification
CREATE TABLE v3_conversation_states (
    session_id VARCHAR PRIMARY KEY,
    mode VARCHAR NOT NULL CHECK (mode IN ('advisory', 'application', 'completion')),
    current_stage VARCHAR NOT NULL,
    captured_context JSONB,
    intent_analysis JSONB,
    confidence_scores JSONB,
    loan_snapshot JSONB,
    recommendations JSONB,
    documents_checklist JSONB,
    stp_checkpoints JSONB,
    stp_status VARCHAR,
    conversation_history JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for performance
CREATE INDEX idx_v3_states_mode ON v3_conversation_states(mode);
CREATE INDEX idx_v3_states_stp_status ON v3_conversation_states(stp_status);
CREATE INDEX idx_v3_states_updated_at ON v3_conversation_states(updated_at);
```

#### 1.2 State Persistence Layer Specification

```python
class StatePersistenceLayer:
    """
    Formal specification:
    
    Invariants:
    - save(state) → ∀ fields: retrieved.field = state.field
    - delete(id) → ¬∃ state: state.session_id = id
    - get(id) → state.session_id = id ∨ None
    
    Safety properties:
    - Concurrent saves are serialized
    - Failed transactions are rolled back
    - No partial writes
    """
    
    def save(self, state: AgenticOrchestratorState) -> bool:
        """
        Postcondition: state exists in database with all fields
        """
        pass
    
    def get(self, session_id: str) -> Optional[AgenticOrchestratorState]:
        """
        Postcondition: returned state has session_id = input session_id
        """
        pass
    
    def delete(self, session_id: str) -> bool:
        """
        Postcondition: ¬∃ state in database: state.session_id = session_id
        """
        pass
```

#### 1.3 Validation Tests (Phase 1)

```python
class TestPhase1Persistence:
    """
    Formal verification tests for Phase 1
    """
    
    def test_state_survives_restart(self):
        """
        Specification: ∀ state: save(state) → get(state.id) = state
        """
        pass
    
    def test_concurrent_updates_serialized(self):
        """
        Specification: concurrent saves → final state = sequential saves
        """
        pass
    
    def test_transaction_rollback_on_failure(self):
        """
        Specification: failed save → database unchanged
        """
        pass
    
    def test_state_reconstruction_lossless(self):
        """
        Specification: ∀ fields: decode(encode(state)).field = state.field
        """
        pass
```

---

### Phase 2: Core API Endpoints

#### 2.1 Endpoint Specifications

**Endpoint: GET /api/v3/conversations/{session_id}/loan**

```
Precondition: session_id exists in database
Postcondition: 
  - 200 OK with loan object if loan exists
  - 404 Not Found if no loan associated
  
Response Schema:
{
  "id": UUID,
  "borrowerName": String,
  "loanType": String,
  "loanAmount": Decimal,
  "interestRate": Decimal,
  "tenure": Integer,
  "monthlyEmi": Decimal,
  ...
}
```

**Endpoint: GET /api/v3/conversations/{session_id}/messages**

```
Precondition: session_id exists
Postcondition:
  - 200 OK with ordered message list
  - 200 OK with empty list if no messages
  
Response Schema:
[
  {
    "id": UUID,
    "conversationId": UUID,
    "role": "user" | "assistant",
    "content": String,
    "metadata": Object,
    "createdAt": ISO8601
  }
]
```

#### 2.2 Validation Tests (Phase 2)

```python
class TestPhase2Endpoints:
    """
    Formal verification tests for Phase 2
    """
    
    def test_get_loan_returns_correct_schema(self):
        """
        Specification: response conforms to LoanResponse schema
        """
        pass
    
    def test_get_messages_returns_chronological_order(self):
        """
        Specification: ∀ i < j: messages[i].createdAt ≤ messages[j].createdAt
        """
        pass
    
    def test_404_for_nonexistent_conversation(self):
        """
        Specification: get(∅) → 404
        """
        pass
    
    def test_correlation_id_propagated(self):
        """
        Specification: ∀ request: response.X-Correlation-ID = request.X-Correlation-ID
        """
        pass
```

---

### Phase 3: Integration Layer

#### 3.1 Adapter Pattern Specification

```python
class V2ToV3Adapter:
    """
    Converts v2 conversation format to v3 state
    
    Invariant: adapt(v2_conv) produces valid v3 state
    """
    
    def adapt(self, v2_conv: V2Conversation) -> AgenticOrchestratorState:
        """
        Postcondition:
          - result.session_id = v2_conv.id
          - result.captured_context.borrower_name = v2_conv.borrowerName
          - result.mode inferred from v2_conv.status
        """
        pass


class V3ToV2Transformer:
    """
    Converts v3 state to v2 conversation format for frontend
    
    Invariant: transform(v3_state) produces valid v2 response
    """
    
    def transform(self, v3_state: AgenticOrchestratorState) -> V2Conversation:
        """
        Postcondition:
          - result.id = v3_state.session_id
          - result.borrowerName = v3_state.captured_context.borrower_name
          - result.status mapped from v3_state.mode
        """
        pass
```

#### 3.2 Validation Tests (Phase 3)

```python
class TestPhase3Integration:
    """
    Formal verification tests for Phase 3
    """
    
    def test_v2_to_v3_roundtrip_preserves_data(self):
        """
        Specification: transform(adapt(v2)) ≈ v2 (lossless for common fields)
        """
        pass
    
    def test_officer_dashboard_sees_v3_conversations(self):
        """
        Specification: v3 conversations appear in v2 listing
        """
        pass
    
    def test_borrower_chat_sees_v2_loans(self):
        """
        Specification: v2 loans accessible from v3 chat
        """
        pass
```

---

## 📊 Success Metrics

### Quantitative Metrics

| Metric | Baseline (v2) | Target (v3) | Measurement Method |
|--------|---------------|-------------|-------------------|
| State persistence | 0% (in-memory) | 100% | Restart test |
| API endpoint coverage | 40% | 100% | OpenAPI spec diff |
| Test coverage | 65% | >90% | pytest-cov report |
| P99 latency | 250ms | <300ms | Locust load test |
| Error rate | 0.1% | <0.5% | Prometheus metrics |

### Qualitative Metrics

- [ ] Code review approval from 2+ senior engineers
- [ ] Architecture review board sign-off
- [ ] Security audit passed
- [ ] Documentation completeness verified

---

## 🔄 Rollback Procedures

### Phase-Specific Rollback

Each phase includes a rollback trigger:

```
IF Phase N validation fails ≥3 times:
  1. Revert code changes (git revert)
  2. Restore database from backup
  3. Restart services
  4. Document failure mode
  5. Re-assess approach
```

### Emergency Rollback Command

```bash
# Rollback to v2-only state
git revert HEAD~5..HEAD  # Revert last 5 commits (1 phase)
docker compose -f infrastructure/docker-compose.yml restart
python scripts/rollback_db.py  # Restore v2 schema
```

---

## 📅 Timeline

```
Week 1: Phase 1 - Database Foundation
  Day 1-2: Schema design & review
  Day 3-4: Implementation
  Day 5: Validation & sign-off

Week 2: Phase 2 - Core API Endpoints
  Day 1-2: Endpoint implementation
  Day 3: Integration with Phase 1
  Day 4-5: Validation & sign-off

Week 3: Phase 3 - Integration Layer
  Day 1-2: Adapter implementation
  Day 3: Cross-version testing
  Day 4-5: Validation & sign-off

Week 4: Phase 4 - Validation Suite
  Day 1-2: Unit tests
  Day 3: Integration tests
  Day 4: E2E tests
  Day 5: Performance benchmarks

Week 5: Phase 5 - Production Hardening
  Day 1-2: Observability integration
  Day 3: Backup/recovery testing
  Day 4: Documentation
  Day 5: Final review & sign-off
```

---

## 🔐 Ethical Considerations

1. **Data Privacy:** All conversation data must be encrypted at rest
2. **Audit Trail:** All state changes must be logged
3. **User Consent:** Borrowers must consent to AI-driven processing
4. **Bias Mitigation:** Agentic decisions must be explainable
5. **Human Oversight:** Escalation path to human officers required

---

## 📚 References

1. **Domain-Driven Design** - Evans, E. (2003)
2. **Designing Data-Intensive Applications** - Kleppmann, M. (2017)
3. **Accelerate** - Forsgren, N. et al. (2018)
4. **Site Reliability Engineering** - Beyer, B. et al. (2016)
5. **Python Type System Documentation** - python.org
6. **FastAPI Best Practices** - tiangolo/fastapi
7. **LangGraph Documentation** - langchain-ai/langgraph

---

**Document Approval:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Lead Researcher | | | |
| Engineering Lead | | | |
| QA Lead | | | |
| Security Lead | | | |

---

**Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-26 | AI Research Assistant | Initial draft |
