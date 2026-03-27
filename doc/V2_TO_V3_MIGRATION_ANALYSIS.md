# KS-LOS v2 to v3 Migration - Comprehensive Problem Analysis

**Date:** March 26, 2026  
**Status:** Critical - Migration Incomplete  
**Impact:** Frontend using v3 endpoints, backend partially v2/v3 hybrid

---

## Executive Summary

The project is in a **broken transitional state** between v2 (deterministic workflow) and v3 (agentic workflow). The frontend has been updated to use v3 endpoints (`/api/v3/conversations/*`), but the backend implementation is incomplete with missing endpoints, mixed router registrations, and deprecated code still active.

### Root Cause
The `launch_dev.sh` script correctly starts the application, but **`src/main.py` registers BOTH v2 and v3 routers simultaneously**, creating conflicts. The frontend exclusively calls v3 endpoints, but many v3 endpoints are missing or incomplete.

---

## 🔴 CRITICAL ISSUES

### 1. **Missing V3 Endpoints** (Frontend Breaking)

The frontend (`ChatInterface.tsx`, `App.tsx`) calls these endpoints that **DO NOT EXIST**:

| Endpoint | Called By | Status | Impact |
|----------|-----------|--------|--------|
| `GET /api/v3/conversations/{id}/loan` | `ChatInterface.tsx:647` | ❌ 404 | Loan snapshot not loading |
| `GET /api/v3/conversations/{id}/messages` | `ChatInterface.tsx:662` | ❌ 404 | Messages not loading |
| `GET /api/v3/conversations/{id}` | `ChatInterface.tsx:892` | ⚠️ Partial | Returns state, not V2Conversation format |
| `POST /api/v3/conversations` | `ChatInterface.tsx:1029` | ✅ Works | Conversation creation works |
| `POST /api/v3/conversations/{id}/messages` | `ChatInterface.tsx:956` | ✅ Works | Message sending works |

**Additional endpoints frontend expects (from App.tsx):**
- `GET /api/conversations` (v2 endpoint, still works)
- `PATCH /api/conversations/{id}` (v2 endpoint)
- `GET /api/phases/active` (v2 endpoint)
- `GET /api/loans` (v2 endpoint)
- `POST /api/loans/{id}/accept-terms` (v2 endpoint)
- `POST /api/loans/{id}/stp-process` (v2 endpoint)

---

### 2. **Router Registration Conflicts** (`src/main.py`)

**Current State:**
```python
# Line 118-128: BOTH v2 AND v3 routers registered
app.include_router(v2_conversations_router)      # v2: /api/conversations
app.include_router(v2_borrower_router)           # v2: /api/borrower
app.include_router(v2_phases_router)             # v2: /api/phases
app.include_router(v2_loans_router)              # v2: /api/loans
app.include_router(v2_catalog_products_router)   # v2: /api/catalog-products
app.include_router(v2_documents_router)          # v2: /api/documents
app.include_router(v2_loan_acceptance_router)    # v2: /api/loans (acceptance)
app.include_router(v3_agentic_router)            # v3: /api/v3/conversations
```

**Problem:** 
- Frontend uses **v3 for conversations** but **v2 for loans/phases/documents**
- No clear migration path - hybrid state creates confusion
- v3 router should be the **primary** interface, but v2 routers are still active

---

### 3. **V3 Router Incomplete Implementation**

**File:** `src/api/routers/v3_agentic_conversations_router.py`

**Missing Endpoints:**
```python
# These need to be added to v3_agentic_conversations_router.py:

@router.get("/{session_id}/loan")
async def get_loan_for_conversation(session_id: str):
    """Get loan associated with this conversation"""
    # Implementation needed

@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    """Get all messages for conversation"""
    # Implementation needed

@router.get("/{session_id}")
async def get_conversation_full(session_id: str):
    """Get full conversation in V2 format for frontend compatibility"""
    # Current implementation returns V3 format, needs V2Compatibility layer
```

**Current Implementation Issues:**
- Line 78-101: `create_conversation` returns v2-compatible format ✅
- Line 103-221: `send_message` returns v2-compatible format ✅
- Line 226-243: `get_conversation` returns **v3 format only** ❌ (should support v2 format)
- Missing: `/loan`, `/messages` endpoints entirely ❌

---

### 4. **Frontend API Call Inconsistencies**

**File:** `frontend/src/App.tsx` and `frontend/src/components/ChatInterface.tsx`

**Mixed Version Usage:**

```typescript
// ChatInterface.tsx uses V3:
const res = await fetch(`http://localhost:8000/api/v3/conversations/${activeConversationId}/loan`);
const res = await fetch(`${API_BASE_URL}/api/v3/conversations/${activeConversationId}/messages`);

// App.tsx uses V2 (Officer Dashboard):
const res = await fetch('http://localhost:8000/api/conversations');  // V2!
const res = await fetch(`http://localhost:8000/api/conversations/${selected.id}`);  // V2!
```

**Problem:** 
- **Borrower chat interface** → V3 endpoints ✅ (correct direction)
- **Officer dashboard** → V2 endpoints ❌ (should migrate to V3)

---

### 5. **Database Schema Issues**

**File:** `src/shared/db.py`

**Current Tables:**
- `conversations` - V2 format (has `approval_probability`, `recommended_products` as JSON)
- `messages` - Basic format (no v3-specific fields)
- `loans` - V2 format (has all v2 fields)
- `loan_phases` - V2 phases
- `loan_documents` - V2 documents
- `loan_product_catalog` - V2 catalog

**Missing V3 Tables:**
- No table for storing `AgenticOrchestratorState`
- V3 state stored **in-memory only** (`STATE_STORE: Dict[str, AgenticOrchestratorState]`)
- **Data loss on restart** - all conversation state lost

**Required Schema Changes:**
```python
class V3ConversationState(Base):
    __tablename__ = "v3_conversation_states"
    
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str]  # advisory/application/completion
    current_stage: Mapped[str]
    captured_context: Mapped[dict]  # JSON
    intent_analysis: Mapped[dict]  # JSON
    confidence_scores: Mapped[dict]  # JSON
    loan_snapshot: Mapped[dict]  # JSON
    recommendations: Mapped[list]  # JSON
    documents_checklist: Mapped[dict]  # JSON
    stp_checkpoints: Mapped[list]  # JSON
    conversation_history: Mapped[list]  # JSON
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

---

### 6. **Deprecated Code Still Active**

**File:** `src/agents/orchestrator.py`

```python
# Line 5: Explicitly marked as DEPRECATED
"""
This orchestrator is DEPRECATED and will be removed in v3.0.
"""

# Line 47-50: Deprecation warning
warnings.warn(
    "LNAIOrchestrator is deprecated and will be removed in KS-LOS v3.0. "
    "Use AgenticOrchestratorState + Node-based workflow instead.",
    DeprecationWarning
)
```

**Still Being Used:**
- `src/agents/agent_tools/document_requirements.py` imports from deprecated orchestrator
- `src/agents/nodes/application_node.py` imports `DocumentsChecklist` from deprecated orchestrator
- Multiple schema definitions duplicated between v2 and v3

**Files with Deprecated Imports:**
```python
# Should be refactored to use v3 equivalents:
from src.agents.orchestrator import DocumentsChecklist  # ❌ DEPRECATED
# Should be:
from src.agents.graph_state import DocumentsChecklist  # ✅ (if exists)
```

---

### 7. **State Management Architecture Conflict**

**V2 Approach (Database-Backed):**
- State stored in PostgreSQL/SQLite
- Persistent across restarts
- Accessed via SQLAlchemy sessions

**V3 Approach (In-Memory):**
- State stored in `STATE_STORE: Dict[str, AgenticOrchestratorState]`
- Lost on server restart
- No database persistence

**Impact:**
- V3 conversations **disappear** after backend restart
- No audit trail for v3 conversations
- Cannot query v3 state via SQL

---

### 8. **Metrics Naming Confusion**

**File:** `src/shared/metrics.py`

```python
# All metrics still use "v2_" prefix:
v2_conversations_created_total
v2_messages_sent_total
v2_loans_created_total
v2_phase_actions_total
```

**Problem:**
- V3 conversations incrementing `v2_` metrics
- Metrics dashboard will show incorrect data
- Should be version-agnostic or use `v3_` prefix

---

## 📋 DETAILED PROBLEM LIST

### Category A: Missing Endpoints (Critical)

| # | Endpoint | Method | Purpose | Priority |
|---|----------|--------|---------|----------|
| A1 | `/api/v3/conversations/{id}/loan` | GET | Get loan for conversation | 🔴 Critical |
| A2 | `/api/v3/conversations/{id}/messages` | GET | Get message history | 🔴 Critical |
| A3 | `/api/v3/conversations/{id}` | GET | Get conversation (v2 format) | 🔴 Critical |
| A4 | `/api/v3/conversations/{id}/loan` | POST | Create/update loan | 🟡 High |
| A5 | `/api/v3/loans` | GET | List all loans (v3) | 🟡 High |
| A6 | `/api/v3/loans/{id}` | GET | Get loan details (v3) | 🟡 High |
| A7 | `/api/v3/phases/active` | GET | Get active phases (v3) | 🟡 High |
| A8 | `/api/v3/documents/loan/{loan_id}` | GET | Get documents for loan | 🟡 High |

---

### Category B: Router Conflicts (High)

| # | Issue | Impact | Solution |
|---|-------|--------|----------|
| B1 | Both v2 and v3 routers active | Confusion, maintenance burden | Deprecate v2 routers gradually |
| B2 | Frontend officer dashboard uses v2 | Inconsistent UX | Migrate to v3 |
| B3 | No versioning strategy | Breaking changes | Use URL versioning consistently |
| B4 | v3 router imports v2 metrics | Metric pollution | Create v3-specific metrics |

---

### Category C: Data Persistence (High)

| # | Issue | Risk | Solution |
|---|-------|------|----------|
| C1 | V3 state in-memory only | Data loss on restart | Add DB persistence |
| C2 | No migration path v2→v3 | Legacy data orphaned | Create migration script |
| C3 | Conversation history not saved | No audit trail | Save to `messages` table |
| C4 | No backup/recovery for v3 | Production risk | Implement state snapshots |

---

### Category D: Code Quality (Medium)

| # | Issue | Technical Debt | Solution |
|---|-------|----------------|----------|
| D1 | Deprecated orchestrator still imported | Maintenance burden | Remove all imports |
| D2 | Duplicate schema definitions | Inconsistency risk | Single source of truth |
| D3 | Mixed v2/v3 format responses | Frontend complexity | Adapter layer |
| D4 | No type safety between versions | Runtime errors | TypeScript/Pydantic guards |

---

## 🛠️ RECOMMENDED FIXES

### Phase 1: Critical Endpoint Implementation (Immediate)

**File:** `src/api/routers/v3_agentic_conversations_router.py`

Add these endpoints:

```python
@router.get("/{session_id}/loan", response_model=Optional[Dict[str, Any]])
async def get_loan_for_conversation(session_id: str, db: Session = Depends(get_db)):
    """Get loan associated with conversation session"""
    from src.shared.db import Loan
    loan = db.query(Loan).filter(Loan.conversation_id == session_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Return in V2 format for frontend compatibility
    return {
        "id": loan.id,
        "borrowerName": loan.borrower_name,
        "loanType": loan.loan_type,
        "loanAmount": loan.loan_amount,
        # ... map all fields
    }

@router.get("/{session_id}/messages", response_model=List[Dict[str, Any]])
async def get_messages(session_id: str, db: Session = Depends(get_db)):
    """Get all messages for conversation"""
    from src.shared.db import Message
    messages = db.query(Message).filter(
        Message.conversation_id == session_id
    ).order_by(Message.created_at).all()
    
    return [
        {
            "id": msg.id,
            "conversationId": msg.conversation_id,
            "role": msg.role,
            "content": msg.content,
            "metadata": msg.metadata_json,
            "createdAt": msg.created_at.isoformat(),
        }
        for msg in messages
    ]

@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_conversation_v2_format(session_id: str, db: Session = Depends(get_db)):
    """Get conversation in V2 format for frontend compatibility"""
    # Try to get from V3 state store first
    if session_id in STATE_STORE:
        state = STATE_STORE[session_id]
        # Convert to V2Conversation format
        return {
            "id": session_id,
            "borrowerName": state.captured_context.borrower_name,
            "status": "active",
            "chatRole": "borrower",
            # ... map to V2 format
        }
    
    # Fallback to database
    from src.shared.db import Conversation
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": conv.id,
        "borrowerName": conv.borrower_name,
        "status": conv.status,
        # ... V2 format
    }
```

---

### Phase 2: Database Persistence (Short-term)

**File:** `src/shared/db.py`

Add V3 state table:

```python
class V3ConversationState(Base):
    __tablename__ = "v3_conversation_states"
    
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="advisory")
    current_stage: Mapped[str] = mapped_column(Text, nullable=False)
    captured_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    intent_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    loan_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    documents_checklist: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    stp_checkpoints: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    stp_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conversation_history: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Update `get_or_create_state` function to use database:

```python
def get_or_create_state(session_id: str, db: Session, borrower_name: Optional[str] = None) -> AgenticOrchestratorState:
    """Get or create state from database"""
    from src.shared.db import V3ConversationState
    
    db_state = db.query(V3ConversationState).filter(
        V3ConversationState.session_id == session_id
    ).first()
    
    if db_state:
        # Reconstruct state from DB
        state = AgenticOrchestratorState(
            session_id=db_state.session_id,
            mode=ConversationMode(db_state.mode),
            current_stage=db_state.current_stage,
            captured_context=CapturedContext(**(db_state.captured_context or {})),
            # ... reconstruct all fields
        )
    else:
        # Create new
        state = create_initial_state(session_id)
        if borrower_name:
            state.captured_context.borrower_name = borrower_name
        
        # Save to DB
        db_state = V3ConversationState(
            session_id=session_id,
            mode=state.mode.value,
            current_stage=state.current_stage,
            captured_context=state.captured_context.model_dump(),
            # ... save all fields
        )
        db.add(db_state)
        db.commit()
    
    return state
```

---

### Phase 3: Router Consolidation (Medium-term)

**Strategy:** Gradual migration from v2 to v3

1. **Keep v2 routers for officer dashboard** (backward compatibility)
2. **Add v3 equivalents** for all v2 endpoints
3. **Update frontend officer dashboard** to use v3
4. **Deprecate v2 routers** with warnings
5. **Remove v2 routers** in v3.0 release

**Timeline:**
- Week 1-2: Implement missing v3 endpoints (Phase 1)
- Week 3-4: Add DB persistence (Phase 2)
- Week 5-6: Migrate officer dashboard to v3
- Week 7-8: Deprecation warnings for v2
- Week 9-10: Remove v2 routers

---

### Phase 4: Code Cleanup (Ongoing)

**Remove deprecated imports:**

```bash
# Find all deprecated imports:
grep -r "from src.agents.orchestrator import" src/

# Replace with v3 equivalents:
# OLD: from src.agents.orchestrator import DocumentsChecklist
# NEW: from src.agents.graph_state import DocumentsChecklist
```

**Consolidate schema definitions:**
- Single source for `DocumentsChecklist`
- Single source for `LoanSnapshot`
- Single source for `LoanRecommendation`

---

## 📊 IMPACT ASSESSMENT

### Current User Impact
- ✅ **Borrower chat**: Works (create + send message)
- ❌ **Borrower chat**: Loan details not loading (404)
- ❌ **Borrower chat**: Message history not loading (404)
- ⚠️ **Officer dashboard**: Works but using deprecated v2 API
- ❌ **Data persistence**: All v3 conversations lost on restart

### Developer Impact
- Confusion about which router to use
- Duplicate code maintenance
- Breaking changes between versions
- No clear migration documentation

### Production Readiness
**Current Status:** ❌ **NOT PRODUCTION READY**

**Blockers:**
1. Data loss on restart (in-memory state)
2. Missing critical endpoints
3. No audit trail for v3 conversations
4. Mixed v2/v3 state creates inconsistency

---

## 🎯 SUCCESS CRITERIA

### Phase 1 Complete When:
- [ ] All missing v3 endpoints implemented
- [ ] Frontend ChatInterface loads without 404 errors
- [ ] Loan details display correctly
- [ ] Message history loads correctly

### Phase 2 Complete When:
- [ ] V3 state persisted to database
- [ ] Conversations survive backend restart
- [ ] State can be queried via SQL
- [ ] Audit trail maintained

### Phase 3 Complete When:
- [ ] Officer dashboard migrated to v3
- [ ] V2 routers marked deprecated
- [ ] Migration guide documented
- [ ] Zero v2 dependencies in new code

### Production Ready When:
- [ ] All Phase 1-3 complete
- [ ] Load testing passed (100 concurrent users)
- [ ] Monitoring/alerting configured
- [ ] Backup/recovery tested
- [ ] Documentation complete

---

## 📝 APPENDIX

### A. File Inventory

**V3 Implementation Files:**
- `src/api/routers/v3_agentic_conversations_router.py` (main v3 router)
- `src/agents/graph_state.py` (v3 state schema)
- `src/agents/nodes/advisory_node.py`
- `src/agents/nodes/application_node.py`
- `src/agents/nodes/completion_node.py`
- `src/agents/nodes/rag_node.py`
- `src/agents/nodes/repair_node.py`
- `src/agents/nodes/escalation_node.py`

**V2 Implementation Files (still active):**
- `src/api/routers/v2_conversations_router.py`
- `src/api/routers/v2_loans_router.py`
- `src/api/routers/v2_phases_router.py`
- `src/api/routers/v2_documents_router.py`
- `src/api/routers/v2_loan_acceptance_router.py`
- `src/api/routers/v2_catalog_products_router.py`

**Deprecated Files:**
- `src/agents/orchestrator.py` (marked for removal)
- `src/agents/llm_integration.py` (legacy)
- `src/agents/nodes_legacy.py` (backup, can be removed)

### B. Frontend Files Using Mixed Versions

**V3 Endpoints:**
- `frontend/src/components/ChatInterface.tsx` (borrower chat)
- `frontend/src/api/v3-agent.ts` (v3 API client)
- `frontend/src/api/agent.ts` (wrapper using v3)

**V2 Endpoints:**
- `frontend/src/App.tsx` (officer dashboard)
- `frontend/src/components/BorrowerJourneyTracker.tsx`
- `frontend/src/components/LoanCard.tsx`

### C. Test Coverage

**V3 Tests Needed:**
- [ ] Endpoint integration tests for `/api/v3/conversations/*`
- [ ] State persistence tests
- [ ] Node processing tests (advisory/application/completion)
- [ ] Migration tests (v2 → v3)

**Existing V2 Tests (still pass):**
- `src/tests/test_api.py`
- `src/tests/test_rbac_api.py`
- `frontend/src/App.test.tsx`

---

## 🔗 RELATED ISSUES

- GitHub Issue: #XXX - V3 router missing endpoints
- GitHub Issue: #YYY - State persistence not implemented
- GitHub Issue: #ZZZ - Deprecated orchestrator still in use
- Documentation: `doc/migration-v3.md` (needs creation)

---

**Document Version:** 1.0  
**Last Updated:** March 26, 2026  
**Maintainer:** Development Team
