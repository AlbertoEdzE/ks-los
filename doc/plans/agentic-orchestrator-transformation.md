# Agentic Orchestrator Transformation Plan

**KS-LOS Phase 3 Enhancement: LNAI-Inspired Conversational Intelligence**

**Created:** 2026-03-26  
**Last Updated:** 2026-03-26  
**Status:** 🟡 In Planning  
**Owner:** Development Team  
**Estimated Duration:** 7 weeks (Hybrid Phased Approach)

---

## Executive Summary

### Objective

Transform the current `orchestrator.py` from a **hardcoded state machine** into a **true LLM-driven agentic system** while preserving the deterministic business logic that ensures financial accuracy and regulatory compliance.

### Approach: Hybrid Phased

**Hybrid** = LLM for conversation + Rules for calculations/compliance  
**Phased** = Incremental delivery over 3 phases (low risk, continuous value)

### Expected Outcomes

| Metric | Current | Target |
|--------|---------|--------|
| Intent Recognition Accuracy | ~60% (regex-based) | ~95% (LLM semantic) |
| Conversation Naturalness | Robotic (fixed templates) | Natural (dynamic responses) |
| User Completion Rate | Unknown | +30% improvement |
| Document Upload Rate | Manual trigger | Auto-prompted (context-aware) |
| STP Auto-Processing | Manual trigger | Auto-triggered on doc upload |
| Time to Application Submit | ~8 conversation turns | ~5 conversation turns |

---

## Architecture Overview

### Current State (As-Is)

```
┌─────────────────────────────────────────────────────────┐
│                    orchestrator.py                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  LNAIOrchestrator Class                           │  │
│  │  - Regex-based intent detection                   │  │
│  │  - Hardcoded conversation flow (9 stages)         │  │
│  │  - Template responses (fixed strings)             │  │
│  │  - Manual STP triggering                          │  │
│  │  - No document intelligence                       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              KS-LOS LangGraph Agents                     │
│  (Separate system - not integrated with orchestrator)   │
│  - journey_coach_node                                   │
│  - risk_engine_node                                     │
│  - calculation_node                                     │
└─────────────────────────────────────────────────────────┘
```

**Problem:** Two parallel systems that don't talk to each other.

### Target State (To-Be)

```
┌─────────────────────────────────────────────────────────┐
│           Agentic Orchestrator (LangGraph)               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  LLM-Powered Nodes                                │  │
│  │  - Advisory Node (Mode 1: Understanding)          │  │
│  │  - Application Node (Mode 2: Collection)          │  │
│  │  - Completion Node (Mode 3: STP + Disbursement)   │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                               │
│                          ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Deterministic Engines (Preserved)                │  │
│  │  - Calculation Engine (EMI, FOIR, LTV, APR)       │  │
│  │  - STP Processor (17 checkpoints)                 │  │
│  │  - Document Intelligence (OCR + extraction)       │  │
│  │  - Metro 2 Generator                              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Solution:** Unified agentic system with clear separation of concerns.

---

## Phase 1: LLM-Powered Intent Extraction

**Duration:** 2 weeks  
**Risk Level:** 🟢 Low  
**Value:** Better user understanding, reduced conversation friction

### Goals

1. Replace regex intent detection with LLM semantic understanding
2. Add structured XML tag parsing for LLM outputs
3. Maintain existing state machine (fallback safety)
4. Integrate with KS-LOS Ollama (qwen2.5:7b)

### Tasks

#### 1.1 Create Structured Output Parser

**File:** `src/agents/structured_parser.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 4 hours

**Requirements:**
- Parse XML-tagged JSON blocks from LLM responses
- Support tags: `intent_analysis`, `loan_snapshot`, `loan_recommendations`, `loan_application`, `documents_checklist`, `phase_update`
- Validate against Pydantic schemas
- Graceful fallback on parse failures

**Acceptance Criteria:**
- [ ] Unit tests for each XML tag type
- [ ] 100% parse accuracy on valid JSON
- [ ] Graceful degradation on malformed output
- [ ] <50ms parsing latency

**Dependencies:** None

---

#### 1.2 Port LNAI Borrower System Prompt

**File:** `src/agents/prompts.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 8 hours

**Requirements:**
- Adapt LNAI's 960-line TypeScript prompt to Python
- Maintain 3-mode conversation structure (Advisory → Application → Completion)
- Preserve Caribbean regional context (currencies, documents, employment types)
- Add KS-LOS-specific elements (STP awareness, Metro 2, PGVector RAG)
- Include XML tag output instructions

**Key Sections:**
```python
BORROWER_SYSTEM_PROMPT = """
[Personality & Tone]
- Elegant, confident, reassuring (private wealth advisor vibe)
- ONE INTENT PER TURN rule
- Caribbean regional awareness

[Mode 1: Advisory]
- Step 1: Understand need (purpose, name)
- Step 2: Employment & income
- Step 3: Financial details (amount, debts)
- Step 4: Loan snapshot + 3 recommendations (COMBINED output)

[Mode 2: Application]
- Step 5: Contact capture (email, phone)
- Step 6: Submit application (all 10 required fields)

[Mode 3: Completion]
- STP awareness (auto-processing explanation)
- Step 7: Documents checklist (context-aware)
- Terms acceptance guidance
- Disbursement confirmation

[Structured Output Rules]
- <intent_analysis> after every user message
- <loan_snapshot> + <loan_recommendations> ALWAYS paired
- <loan_application> when all 10 fields collected
- <documents_checklist> with submission
- <phase_update> on progression signals
"""
```

**Acceptance Criteria:**
- [ ] Prompt fits within Ollama context window (8K tokens)
- [ ] Produces valid XML-tagged output consistently
- [ ] Handles Caribbean currency variations (USD, TTD, JMD, etc.)
- [ ] Includes all LNAI pacing rules

**Dependencies:** Task 1.1 (parser must support output format)

---

#### 1.3 Create Intent Extraction Tool

**File:** `src/agents/tools/intent_extractor.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Requirements:**
- LangChain ToolNode-compatible tool
- Input: conversation history (list of messages)
- Output: `CapturedContext` Pydantic model
- Use Ollama (qwen2.5:7b) for extraction
- Confidence scoring (0-1 scale)

**Tool Schema:**
```python
class IntentExtractorTool(BaseTool):
    name = "extract_borrower_intent"
    description = "Extract loan intent and borrower context from conversation"
    
    def _run(self, conversation_history: List[Message]) -> IntentExtractionResult:
        # Call LLM with extraction prompt
        # Parse structured output
        # Validate with Pydantic
        # Return typed context + confidence score
```

**Acceptance Criteria:**
- [ ] Extracts all 11 required fields (purpose, amount, income, employment, etc.)
- [ ] Handles ambiguous inputs gracefully
- [ ] Returns confidence score for each field
- [ ] Integration tests with sample conversations

**Dependencies:** Task 1.2 (prompt defines extraction behavior)

---

#### 1.4 Enhance CapturedContext Schema

**File:** `src/agents/orchestrator.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 2 hours

**Requirements:**
- Add missing fields from LNAI schema
- Add confidence scores per field
- Add currency tracking (USD, TTD, JMD, etc.)
- Add validation rules

**New Schema:**
```python
class CapturedContext(BaseModel):
    # Original fields
    purpose: Optional[str] = None
    loan_amount: Optional[float] = None
    monthly_income: Optional[float] = None
    # ... existing fields
    
    # NEW: LNAI-inspired fields
    urgency: Optional[Literal["low", "medium", "high", "critical"]] = None
    preferred_tenure: Optional[str] = None
    collateral_available: Optional[str] = None
    credit_history: Optional[str] = None
    
    # NEW: Confidence scores (0-1)
    field_confidence: Dict[str, float] = Field(default_factory=dict)
    
    # NEW: Currency tracking
    currency: str = "USD"
    currency_symbol: str = "$"
    
    # NEW: Validation
    @validator('loan_amount')
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Loan amount must be positive")
        return v
```

**Acceptance Criteria:**
- [ ] All fields from LNAI intent_analysis supported
- [ ] Backward compatible with existing code
- [ ] Validation rules prevent invalid data

**Dependencies:** None (schema change only)

---

#### 1.5 Integrate LLM Intent Extraction into Orchestrator

**File:** `src/agents/orchestrator.py` (modify)  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 8 hours

**Requirements:**
- Replace regex detection in `_handle_intent_capture()` with LLM tool call
- Replace regex in `_handle_financial_context()` with LLM extraction
- Add confidence-based fallback logic:
  - Confidence > 0.8: Auto-accept
  - Confidence 0.5-0.8: Ask clarifying question
  - Confidence < 0.5: Use explicit questioning (fallback to templates)
- Preserve state machine structure (safety net)

**Integration Pattern:**
```python
def _handle_intent_capture(self, message: str) -> Dict[str, Any]:
    # Call LLM intent extractor
    result = self.intent_extractor.run(self.conversation_history)
    
    # Check confidence
    if result.confidence > 0.8:
        # Auto-accept extraction
        self.state.captured_context.update(result.context)
    elif result.confidence > 0.5:
        # Ask clarifying question for low-confidence fields
        return self._ask_clarification(result.low_confidence_fields)
    else:
        # Fallback to explicit questioning
        return self._fallback_explicit_questioning()
    
    # Continue with existing flow...
```

**Acceptance Criteria:**
- [ ] Handles all LNAI intent patterns (home, auto, personal, business, etc.)
- [ ] Graceful degradation on LLM failure
- [ ] Maintains conversation history for context
- [ ] Unit tests for confidence-based routing

**Dependencies:** Tasks 1.1, 1.2, 1.3, 1.4

---

#### 1.6 Add XML Tag Response Generation

**File:** `src/agents/orchestrator.py` (modify)  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Requirements:**
- Generate XML-tagged responses for UI cards:
  - `<loan_snapshot>` after financial context complete
  - `<loan_recommendations>` paired with snapshot
  - `<documents_checklist>` on application submission
- Maintain natural language chat text alongside XML tags
- Ensure frontend can parse and render cards

**Response Format:**
```python
response = (
    "I've analyzed your financials and put together the ideal path for you. "
    "Here are your top options, with my recommendation highlighted.\n\n"
    "<loan_snapshot>\n"
    "{...JSON...}\n"
    "</loan_snapshot>\n\n"
    "<loan_recommendations>\n"
    "{...JSON array...}\n"
    "</loan_recommendations>"
)
```

**Acceptance Criteria:**
- [ ] Frontend correctly renders cards from XML tags
- [ ] Chat text remains natural (not robotic)
- [ ] All card types supported (snapshot, recommendations, documents, application)
- [ ] E2E tests for card rendering

**Dependencies:** Task 1.5 (integration must be complete)

---

#### 1.7 Create Unit Tests for Phase 1

**File:** `src/tests/test_orchestrator_phase1.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Test Coverage:**
- [ ] XML parser tests (valid JSON, malformed JSON, missing tags)
- [ ] Intent extraction tests (all loan purposes, edge cases)
- [ ] Confidence-based routing tests (high/medium/low confidence)
- [ ] Conversation flow tests (complete advisory mode flow)
- [ ] Error handling tests (LLM unavailable, timeout, invalid output)

**Acceptance Criteria:**
- [ ] 90%+ code coverage for new code
- [ ] All tests pass in CI/CD
- [ ] Integration tests run with Ollama

**Dependencies:** All Phase 1 tasks

---

### Phase 1 Deliverables

| Deliverable | Description | Status |
|-------------|-------------|--------|
| `structured_parser.py` | XML tag extraction + validation | ⚪ Not Started |
| `prompts.py` | LNAI-style system prompts | ⚪ Not Started |
| `tools/intent_extractor.py` | LLM-powered intent extraction | ⚪ Not Started |
| Enhanced `orchestrator.py` | LLM integration with fallback | ⚪ Not Started |
| Unit test suite | 90%+ coverage | ⚪ Not Started |
| Documentation | API docs, usage examples | ⚪ Not Started |

### Phase 1 Success Metrics

- [ ] Intent recognition accuracy > 90% (measured on test conversations)
- [ ] Average conversation turns to loan snapshot < 6
- [ ] Zero regression in existing functionality
- [ ] All unit tests passing
- [ ] Manual QA sign-off on conversation naturalness

---

## Phase 2: Document Intelligence & Auto-Processing

**Duration:** 2 weeks  
**Risk Level:** 🟡 Medium  
**Value:** Reduced manual data entry, faster STP processing

### Goals

1. Enhance OCR with intelligent field extraction
2. Auto-populate loan application from uploaded documents
3. Context-aware document checklist generation
4. Auto-trigger STP on minimum document threshold

### Tasks

#### 2.1 Create Document Intelligence Engine

**File:** `src/core/document_intelligence.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 12 hours

**Requirements:**
- OCR with Tesseract (existing) + field extraction (new)
- Document type classification (ID, pay slip, bank statement, tax return)
- Structured field extraction per document type:
  - **ID:** name, ID number, expiry date, nationality
  - **Pay Slip:** employer name, gross pay, net pay, deductions, pay period
  - **Bank Statement:** account balance, average balance, transaction count
  - **Tax Return:** declared income, business type, filing year
- Confidence scoring per extracted field
- Validation against user-declared information

**Extraction Pipeline:**
```python
class DocumentIntelligence:
    def extract(self, document: LoanDocument) -> ExtractionResult:
        # Step 1: OCR
        text = self.ocr_engine.extract_text(document.file_path)
        
        # Step 2: Classify document type
        doc_type = self.classifier.predict(text)  # ID, pay_slip, etc.
        
        # Step 3: Extract fields based on type
        fields = self.extractors[doc_type].extract(text)
        
        # Step 4: Validate & score confidence
        validated = self.validate(fields)
        
        return ExtractionResult(
            document_type=doc_type,
            fields=validated,
            confidence_scores=self.compute_confidence(fields),
            flags=self.detect_anomalies(fields)
        )
```

**Acceptance Criteria:**
- [ ] Supports 4+ document types (ID, pay slip, bank statement, tax return)
- [ ] Field extraction accuracy > 85% (tested on sample documents)
- [ ] Processing time < 5 seconds per document
- [ ] Confidence scores correlate with actual accuracy

**Dependencies:** None (new component)

---

#### 2.2 Create Document Requirements Tool

**File:** `src/agents/tools/document_requirements.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 4 hours

**Requirements:**
- Generate context-aware document checklists
- Port LNAI's `getDocumentCategories()` logic
- Support loan type variations (home, auto, personal, business)
- Support employment type variations (salaried, self-employed)
- Return structured `DocumentsChecklist` model

**Tool Logic:**
```python
class DocumentRequirementsTool(BaseTool):
    def _run(
        self,
        loan_type: str,
        employment_type: str,
        loan_amount: float
    ) -> DocumentsChecklist:
        checklist = DocumentsChecklist()
        
        # Always required
        checklist.identity = [
            {"name": "National ID or Passport", "required": True},
            {"name": "Proof of Address", "required": True}
        ]
        
        # Employment-based
        if employment_type == "salaried":
            checklist.income = [
                {"name": "Job Letter", "required": True},
                {"name": "Last 3 Months' Pay Slips", "required": True},
                {"name": "Bank Statements (6 months)", "required": True}
            ]
        else:  # self-employed
            checklist.income = [
                {"name": "Business Registration", "required": True},
                {"name": "Financial Statements (2 years)", "required": True},
                {"name": "Tax Returns (2 years)", "required": True}
            ]
        
        # Loan type-based
        if loan_type == "home_purchase":
            checklist.property = [
                {"name": "Sale Agreement", "required": True},
                {"name": "Valuation Report", "required": True}
            ]
        
        return checklist
```

**Acceptance Criteria:**
- [ ] Generates correct checklists for all loan/employment combinations
- [ ] Returns structured data compatible with frontend
- [ ] Unit tests for all combinations

**Dependencies:** Task 2.1 (understands document types)

---

#### 2.3 Auto-Populate Application from Documents

**File:** `src/agents/nodes/document_processor_node.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 8 hours

**Requirements:**
- Listen for document upload events
- Run Document Intelligence extraction
- Auto-populate `CapturedContext` fields:
  - From ID: borrower name, nationality
  - From pay slips: employer name, monthly income
  - From bank statements: average balance (corroborate income)
  - From tax returns: declared income (self-employed)
- Flag discrepancies between uploaded docs and user-declared info
- Update conversation state

**Auto-Population Logic:**
```python
class DocumentProcessorNode:
    def process(self, state: OrchestratorState) -> OrchestratorState:
        for doc in state.uploaded_documents:
            if not doc.processed:
                extraction = self.document_intelligence.extract(doc)
                
                # Auto-fill fields
                if extraction.document_type == "pay_slip":
                    extracted_income = extraction.fields.get("gross_pay")
                    declared_income = state.captured_context.monthly_income
                    
                    # Check for discrepancy
                    if declared_income and abs(extracted_income - declared_income) > 0.2 * declared_income:
                        state.flags.append({
                            "type": "income_discrepancy",
                            "declared": declared_income,
                            "extracted": extracted_income,
                            "severity": "high"
                        })
                    else:
                        state.captured_context.monthly_income = extracted_income
                
                doc.processed = True
        
        return state
```

**Acceptance Criteria:**
- [ ] Auto-populates 5+ fields from documents
- [ ] Flags discrepancies > 20% variance
- [ ] Does not overwrite user-confirmed data without flag
- [ ] Integration tests with sample documents

**Dependencies:** Task 2.1 (extraction engine)

---

#### 2.4 Auto-Trigger STP on Document Threshold

**File:** `src/agents/nodes/stp_trigger_node.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Requirements:**
- Define minimum document thresholds per loan type:
  - **Personal Loan:** ID + 1 income proof
  - **Home Loan:** ID + 2 income proofs + 2 property docs
  - **Auto Loan:** ID + 1 income proof + dealer invoice
- Monitor document upload progress
- Auto-trigger STP when threshold met
- Notify user via chat

**Trigger Logic:**
```python
class STPTriggerNode:
    def should_trigger(self, state: OrchestratorState) -> bool:
        uploaded = state.uploaded_documents
        loan_type = state.captured_context.purpose
        
        thresholds = {
            "personal": {"identity": 1, "income": 1},
            "home_purchase": {"identity": 1, "income": 2, "property": 2},
            "auto": {"identity": 1, "income": 1, "vehicle": 1}
        }
        
        threshold = thresholds.get(loan_type, thresholds["personal"])
        
        # Check if threshold met
        for category, count in threshold.items():
            actual = len([d for d in uploaded if d.category == category])
            if actual < count:
                return False
        
        return True
```

**Acceptance Criteria:**
- [ ] Correctly identifies threshold met for each loan type
- [ ] Does not trigger prematurely
- [ ] Sends user notification on trigger
- [ ] Manual override available (officer can trigger early)

**Dependencies:** Task 2.3 (document processing)

---

#### 2.5 Enhance Frontend Document Upload UI

**File:** `frontend/src/components/documents/DocumentUploadPanel.tsx`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 8 hours

**Requirements:**
- Display context-aware checklist (from LLM)
- Show extraction progress per document
- Display auto-populated fields with edit capability
- Show discrepancy warnings
- Real-time upload status (uploading → processing → extracted → verified)

**UI Components:**
```typescript
interface DocumentUploadPanelProps {
  checklist: DocumentsChecklist;  // From LLM
  uploadedDocuments: LoanDocument[];
  extractionResults: ExtractionResult[];
  autoPopulatedFields: Partial<CapturedContext>;
  discrepancies: DiscrepancyFlag[];
}
```

**Acceptance Criteria:**
- [ ] Checklist updates dynamically as conversation progresses
- [ ] Extraction progress visible to user
- [ ] Discrepancy warnings clearly displayed
- [ ] User can edit auto-populated fields
- [ ] Responsive design (mobile + desktop)

**Dependencies:** Task 2.2 (checklist format), Task 2.3 (extraction results)

---

#### 2.6 Create Unit Tests for Phase 2

**File:** `src/tests/test_document_intelligence.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Test Coverage:**
- [ ] OCR extraction tests (sample documents per type)
- [ ] Document classification tests
- [ ] Field extraction accuracy tests
- [ ] Auto-population logic tests
- [ ] STP trigger threshold tests
- [ ] Discrepancy detection tests

**Acceptance Criteria:**
- [ ] 90%+ code coverage
- [ ] All tests pass in CI/CD
- [ ] Integration tests with real document samples

**Dependencies:** All Phase 2 tasks

---

### Phase 2 Deliverables

| Deliverable | Description | Status |
|-------------|-------------|--------|
| `document_intelligence.py` | OCR + field extraction engine | ⚪ Not Started |
| `tools/document_requirements.py` | Context-aware checklist generation | ⚪ Not Started |
| `nodes/document_processor_node.py` | Auto-population from docs | ⚪ Not Started |
| `nodes/stp_trigger_node.py` | Auto-STP on threshold | ⚪ Not Started |
| Enhanced frontend upload UI | Dynamic checklist + extraction status | ⚪ Not Started |
| Unit test suite | 90%+ coverage | ⚪ Not Started |

### Phase 2 Success Metrics

- [ ] Document field extraction accuracy > 85%
- [ ] Auto-population reduces manual entry by 50%
- [ ] STP auto-trigger rate > 80% (vs manual trigger)
- [ ] Document processing time < 5 seconds average
- [ ] User satisfaction score > 4.0/5.0 (post-upload survey)

---

## Phase 3: Full Agentic Flow

**Duration:** 3 weeks  
**Risk Level:** 🟡 Medium-High  
**Value:** Premium conversational experience, reduced maintenance burden

### Goals

1. Migrate from state machine to LangGraph workflow
2. Add LLM-powered response generation (dynamic, not templates)
3. Integrate RAG for policy-grounded responses
4. Add conversation repair mechanisms (handling corrections, digressions)
5. Implement confidence-based routing with human escalation

### Tasks

#### 3.1 Design LangGraph State Schema

**File:** `src/agents/graph_state.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Requirements:**
- Define complete agent state (supersedes `OrchestratorState`)
- Include all LNAI-inspired fields
- Support conversation mode tracking (advisory/application/completion)
- Include document state, STP state, phase state
- Ensure backward compatibility with existing LangGraph nodes

**State Schema:**
```python
class AgenticOrchestratorState(BaseModel):
    # Conversation metadata
    session_id: str
    conversation_mode: Literal["advisory", "application", "completion"]
    conversation_history: List[Message]
    
    # Borrower context (from Phase 1)
    captured_context: CapturedContext
    intent_analysis: Optional[IntentSummary]
    
    # Loan details
    loan_snapshot: Optional[LoanSnapshot]
    recommendations: List[LoanRecommendation]
    selected_recommendation: Optional[LoanRecommendation]
    
    # Documents
    documents_checklist: Optional[DocumentsChecklist]
    uploaded_documents: List[LoanDocument]
    extraction_results: List[ExtractionResult]
    
    # STP processing
    stp_checkpoints: List[STPCheckpoint]
    stp_status: Literal["pending", "processing", "approved", "disbursed"]
    bureau_score: Optional[int]
    
    # Phase progression
    current_phase_id: str
    phase_history: List[PhaseTransition]
    
    # Flags & alerts
    flags: List[DiscrepancyFlag]
    confidence_scores: Dict[str, float]
    
    # UI state
    awaiting_user_input: bool
    last_llm_response: Optional[str]
```

**Acceptance Criteria:**
- [ ] All fields from LNAI schema supported
- [ ] Compatible with existing KS-LOS LangGraph nodes
- [ ] Pydantic validation on all state transitions
- [ ] State serialization for persistence

**Dependencies:** Phase 1 schemas (CapturedContext, etc.)

---

#### 3.2 Create Advisory Mode Node

**File:** `src/agents/nodes/advisory_node.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 10 hours

**Requirements:**
- Implement LNAI Mode 1 (Advisory) logic
- Steps: Understand need → Employment/income → Financial details → Snapshot+Recommendations
- Use LLM for response generation (not templates)
- Enforce "ONE INTENT PER TURN" rule
- Output XML tags for UI cards

**Node Logic:**
```python
class AdvisoryNode:
    def __call__(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        # Determine current step based on captured context
        step = self.determine_step(state)
        
        if step == "understand_need":
            # Ask about loan purpose
            response = self.llm.generate(
                prompt=UNDERSTAND_NEED_PROMPT,
                context=state.conversation_history
            )
        
        elif step == "employment_income":
            # Ask about employment type and income
            response = self.llm.generate(
                prompt=EMPLOYMENT_INCOME_PROMPT,
                context=state.conversation_history
            )
        
        elif step == "financial_details":
            # Ask about loan amount and existing debts
            response = self.llm.generate(
                prompt=FINANCIAL_DETAILS_PROMPT,
                context=state.conversation_history
            )
        
        elif step == "snapshot_and_recommendations":
            # Call calculation engine, generate recommendations
            state.loan_snapshot = self.calculation_engine.compute(state.captured_context)
            state.recommendations = self.product_matcher.find_best(state)
            
            # Generate response with XML tags
            response = self.format_snapshot_and_recommendations(state)
        
        state.conversation_history.append({"role": "assistant", "content": response})
        return state
```

**Acceptance Criteria:**
- [ ] Follows LNAI 4-step advisory flow
- [ ] Generates natural, empathetic responses
- [ ] Outputs valid XML tags for cards
- [ ] Enforces one-intent-per-turn pacing
- [ ] Integration tests for complete advisory flow

**Dependencies:** Task 3.1 (state schema), Phase 1 (prompts, parser)

---

#### 3.3 Create Application Mode Node

**File:** `src/agents/nodes/application_node.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 8 hours

**Requirements:**
- Implement LNAI Mode 2 (Application) logic
- Steps: Contact capture → Submit application
- Validate all 10 required fields before submission
- Generate `<loan_application>` XML tag
- Generate `<documents_checklist>` XML tag
- Trigger document processor node

**Node Logic:**
```python
class ApplicationNode:
    REQUIRED_FIELDS = [
        "first_name", "last_name", "email", "phone",
        "employment_type", "monthly_income", "loan_type",
        "loan_amount", "purpose", "existing_debts"
    ]
    
    def __call__(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        # Check if all required fields collected
        if not self.all_fields_complete(state):
            # Ask for missing fields
            missing = self.get_missing_fields(state)
            response = self.llm.generate(
                prompt=CONTACT_CAPTURE_PROMPT,
                context=state.conversation_history,
                missing_fields=missing
            )
        else:
            # Submit application
            loan = self.create_loan_record(state)
            state.application_id = loan.id
            
            # Generate documents checklist
            state.documents_checklist = self.document_requirements.run(
                loan_type=state.captured_context.purpose,
                employment_type=state.captured_context.employment_type
            )
            
            # Format response with XML tags
            response = self.format_application_submission(state)
        
        state.conversation_history.append({"role": "assistant", "content": response})
        return state
```

**Acceptance Criteria:**
- [ ] Validates all 10 required fields
- [ ] Does not submit until fields complete
- [ ] Generates correct XML tags
- [ ] Creates loan record in database
- [ ] Integration tests for complete application flow

**Dependencies:** Task 3.1 (state schema), Phase 2 (document requirements)

---

#### 3.4 Create Completion Mode Node

**File:** `src/agents/nodes/completion_node.py`  
**Priority:** 🔴 Critical  
**Status:** ⚪ Not Started  
**Estimated Effort:** 10 hours

**Requirements:**
- Implement LNAI Mode 3 (Completion) logic
- STP processing awareness and communication
- Terms acceptance guidance
- Disbursement confirmation
- Celebration messaging

**Node Logic:**
```python
class CompletionNode:
    def __call__(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        # Check STP status
        if state.stp_status == "processing":
            response = self.generate_stp_progress_update(state)
        
        elif state.stp_status == "approved" and not state.terms_accepted:
            response = self.generate_terms_acceptance_prompt(state)
        
        elif state.stp_status == "approved" and state.terms_accepted:
            response = self.generate_disbursement_confirmation(state)
            self.send_disbursement_notifications(state)
        
        elif state.stp_status == "rejected":
            response = self.generate_rejection_message(state)
            self.escalate_to_officer(state)
        
        state.conversation_history.append({"role": "assistant", "content": response})
        return state
```

**Acceptance Criteria:**
- [ ] Communicates STP progress clearly
- [ ] Handles terms acceptance flow
- [ ] Generates disbursement confirmation
- [ ] Handles rejection with empathy
- [ ] Integration tests for all completion scenarios

**Dependencies:** Task 3.1 (state schema), STP processor integration

---

#### 3.5 Add Conversation Repair Mechanisms

**File:** `src/agents/nodes/repair_node.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Requirements:**
- Detect user corrections ("Wait, I meant...", "Actually...")
- Detect digressions (off-topic questions)
- Handle contradictions (new info conflicts with prior)
- Graceful recovery without losing context

**Repair Logic:**
```python
class RepairNode:
    CORRECTION_PATTERNS = [
        r"wait,? i meant",
        r"actually,?",
        r"correction",
        r"that's not right",
        r"i changed my mind"
    ]
    
    def __call__(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        last_message = state.conversation_history[-1]["content"]
        
        # Check for correction pattern
        if self.is_correction(last_message):
            # Identify what's being corrected
            correction_target = self.identify_correction_target(
                last_message,
                state.conversation_history
            )
            
            # Update captured context
            self.update_context_with_correction(state, correction_target)
            
            # Acknowledge and confirm
            response = self.generate_correction_acknowledgment(state)
        
        # Check for digression
        elif self.is_digression(last_message):
            # Acknowledge question
            # Answer briefly
            # Redirect to main flow
            response = self.handle_digression(state)
        
        state.conversation_history.append({"role": "assistant", "content": response})
        return state
```

**Acceptance Criteria:**
- [ ] Detects 90%+ of correction patterns
- [ ] Correctly identifies field being corrected
- [ ] Handles digressions without losing flow
- [ ] User confirmation on significant changes

**Dependencies:** Task 3.1 (state schema)

---

#### 3.6 Integrate RAG for Policy-Grounded Responses

**File:** `src/agents/nodes/rag_node.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 8 hours

**Requirements:**
- Retrieve relevant policies from PGVector knowledge base
- Ground LLM responses in retrieved policies
- Handle policy-based questions ("What's the minimum credit score?")
- Cite policies in responses

**RAG Logic:**
```python
class RAGNode:
    def __call__(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        last_message = state.conversation_history[-1]["content"]
        
        # Check if question is policy-related
        if self.is_policy_question(last_message):
            # Retrieve relevant policies
            policies = self.knowledge_base.search(
                query=last_message,
                k=3
            )
            
            # Generate grounded response
            response = self.llm.generate(
                prompt=POLICY_GROUNDED_PROMPT,
                context=state.conversation_history,
                retrieved_policies=policies
            )
            
            # Add citations
            response = self.add_citations(response, policies)
        
        state.conversation_history.append({"role": "assistant", "content": response})
        return state
```

**Acceptance Criteria:**
- [ ] Retrieves relevant policies for policy questions
- [ ] Responses grounded in retrieved policies
- [ ] Includes citations/links to policies
- [ ] Falls back gracefully if no relevant policies found

**Dependencies:** KS-LOS knowledge base (existing)

---

#### 3.7 Add Confidence-Based Human Escalation

**File:** `src/agents/nodes/escalation_node.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 6 hours

**Requirements:**
- Monitor confidence scores across all extractions
- Define escalation thresholds:
  - LLM confidence < 0.3 for 3+ consecutive turns
  - User expresses frustration (sentiment analysis)
  - Contradictions detected
  - High-value loan (> $500K USD) with any flags
- Create officer handoff with conversation summary
- Notify officer via notification system

**Escalation Logic:**
```python
class EscalationNode:
    def should_escalate(self, state: AgenticOrchestratorState) -> bool:
        # Low confidence streak
        recent_confidences = state.confidence_scores[-5:]
        if sum(recent_confidences) / len(recent_confidences) < 0.3:
            return True
        
        # User frustration
        last_message = state.conversation_history[-1]["content"]
        if self.sentiment_analyzer.is_frustrated(last_message):
            return True
        
        # High-value loan with flags
        if state.captured_context.loan_amount > 500000 and state.flags:
            return True
        
        return False
    
    def escalate(self, state: AgenticOrchestratorState):
        # Create handoff summary
        summary = self.generate_handoff_summary(state)
        
        # Notify officers
        self.notify_officers(summary)
        
        # Inform user
        response = (
            "I want to make sure you get the best assistance for your application. "
            "I'm connecting you with a senior loan officer who will reach out within 24 hours."
        )
        
        return response
```

**Acceptance Criteria:**
- [ ] Escalates on defined thresholds
- [ ] Generates comprehensive handoff summary
- [ ] Notifies officers via existing notification system
- [ ] Informs user with appropriate messaging

**Dependencies:** Task 3.1 (state schema), KS-LOS notification system

---

#### 3.8 Deprecate Old Orchestrator State Machine

**File:** `src/agents/orchestrator.py` (modify)  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 4 hours

**Requirements:**
- Add deprecation warnings to `LNAIOrchestrator` class
- Redirect API calls to new LangGraph workflow
- Maintain backward compatibility for 30 days
- Update documentation

**Deprecation Plan:**
```python
# orchestrator.py
import warnings

class LNAIOrchestrator:
    def __init__(self):
        warnings.warn(
            "LNAIOrchestrator is deprecated and will be removed in v3.0. "
            "Use the LangGraph agentic workflow instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # ... existing code ...

# api/routers/v2_conversations_router.py
from src.agents.graph import run_agentic_workflow

async def process_message(...):
    # Old code:
    # orchestrator = get_orchestrator(session_id)
    # response = orchestrator.process_message(message)
    
    # New code:
    response = await run_agentic_workflow(session_id, message)
```

**Acceptance Criteria:**
- [ ] Deprecation warnings visible in logs
- [ ] API calls routed to new workflow
- [ ] Documentation updated
- [ ] Migration guide for developers

**Dependencies:** All Phase 3 nodes complete and tested

---

#### 3.9 Create Unit Tests for Phase 3

**File:** `src/tests/test_agentic_workflow.py`  
**Priority:** 🟠 High  
**Status:** ⚪ Not Started  
**Estimated Effort:** 10 hours

**Test Coverage:**
- [ ] Advisory mode complete flow tests
- [ ] Application mode complete flow tests
- [ ] Completion mode scenarios (approved, rejected, disbursed)
- [ ] Conversation repair tests (corrections, digressions)
- [ ] RAG integration tests
- [ ] Escalation threshold tests
- [ ] End-to-end conversation tests (full borrower journey)

**Acceptance Criteria:**
- [ ] 90%+ code coverage
- [ ] All tests pass in CI/CD
- [ ] E2E tests run with full infrastructure
- [ ] Performance tests (response time < 3 seconds)

**Dependencies:** All Phase 3 tasks

---

### Phase 3 Deliverables

| Deliverable | Description | Status |
|-------------|-------------|--------|
| `graph_state.py` | Complete agent state schema | ⚪ Not Started |
| `nodes/advisory_node.py` | LNAI Mode 1 implementation | ⚪ Not Started |
| `nodes/application_node.py` | LNAI Mode 2 implementation | ⚪ Not Started |
| `nodes/completion_node.py` | LNAI Mode 3 implementation | ⚪ Not Started |
| `nodes/repair_node.py` | Conversation repair | ⚪ Not Started |
| `nodes/rag_node.py` | Policy-grounded responses | ⚪ Not Started |
| `nodes/escalation_node.py` | Human handoff | ⚪ Not Started |
| LangGraph workflow | Complete agentic flow | ⚪ Not Started |
| Deprecation of old orchestrator | Migration complete | ⚪ Not Started |
| Unit test suite | 90%+ coverage | ⚪ Not Started |

### Phase 3 Success Metrics

- [ ] Conversation naturalness score > 4.5/5.0 (user survey)
- [ ] Average conversation turns to completion < 8
- [ ] Escalation rate < 10% (most conversations handled by agent)
- [ ] Response time < 3 seconds (p95 latency)
- [ ] Zero critical bugs in production (first 30 days)
- [ ] Developer satisfaction > 4.0/5.0 (maintainability survey)

---

## Implementation Timeline

```
Week 1-2: Phase 1 (LLM-Powered Intent Extraction)
├─ Week 1: Tasks 1.1, 1.2, 1.3, 1.4
└─ Week 2: Tasks 1.5, 1.6, 1.7

Week 3-4: Phase 2 (Document Intelligence & Auto-Processing)
├─ Week 3: Tasks 2.1, 2.2, 2.3
└─ Week 4: Tasks 2.4, 2.5, 2.6

Week 5-7: Phase 3 (Full Agentic Flow)
├─ Week 5: Tasks 3.1, 3.2, 3.3
├─ Week 6: Tasks 3.4, 3.5, 3.6
└─ Week 7: Tasks 3.7, 3.8, 3.9
```

### Gantt Chart

```
Task                          W1  W2  W3  W4  W5  W6  W7
────────────────────────────────────────────────────────
Phase 1: Intent Extraction    ███ ███
  1.1 Structured Parser       ██
  1.2 System Prompt              ██
  1.3 Intent Tool                  ██
  1.4 Schema Enhancement      ██
  1.5 Integration                ███
  1.6 XML Response                 ███
  1.7 Tests                        ███
────────────────────────────────────────────────────────
Phase 2: Document Intelligence        ███ ███
  2.1 Document Intelligence         ███
  2.2 Requirements Tool                  ██
  2.3 Auto-Population                  ███
  2.4 STP Trigger                        ███
  2.5 Frontend UI                        ███
  2.6 Tests                              ███
────────────────────────────────────────────────────────
Phase 3: Full Agentic Flow                ███ ███ ███
  3.1 State Schema                          ███
  3.2 Advisory Node                            ███
  3.3 Application Node                          ███
  3.4 Completion Node                            ███
  3.5 Repair Node                                 ███
  3.6 RAG Node                                    ███
  3.7 Escalation Node                              ███
  3.8 Deprecation                                     ███
  3.9 Tests                                          ███
────────────────────────────────────────────────────────
```

---

## Risk Management

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM output inconsistent | Medium | High | XML parser with fallback, confidence scoring |
| OCR accuracy < 85% | Medium | Medium | Human review workflow, confidence thresholds |
| LangGraph performance issues | Low | High | Load testing, caching, async processing |
| Ollama model limitations | Medium | Medium | Fallback to Groq/OpenAI, prompt optimization |
| Frontend parsing failures | Low | Medium | Schema validation, error boundaries |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| User confusion with new flow | Low | Medium | A/B testing, gradual rollout, user feedback |
| Regulatory compliance concerns | Medium | High | Legal review, audit logging, explainable AI |
| Increased support tickets | Medium | Medium | Officer escalation path, clear handoff messaging |
| Timeline slippage | Medium | Medium | Phased approach (each phase delivers value) |

---

## Testing Strategy

### Unit Testing

- **Coverage Target:** 90%+ for all new code
- **Framework:** pytest (backend), Vitest (frontend)
- **Focus Areas:** Parsers, extractors, state transitions, validation

### Integration Testing

- **Scope:** LLM + parser + state machine + database
- **Framework:** pytest with test fixtures
- **Focus Areas:** Complete conversation flows, document processing, STP triggers

### E2E Testing

- **Scope:** Full borrower journey (frontend to backend)
- **Framework:** Playwright
- **Focus Areas:** Chat interface, document upload, STP visualization, terms acceptance

### Performance Testing

- **Metrics:** Response time, throughput, error rate
- **Tool:** Locust or k6
- **Targets:**
  - p95 response time < 3 seconds
  - Throughput > 100 concurrent conversations
  - Error rate < 0.1%

### User Acceptance Testing

- **Participants:** 10-15 internal users (diverse backgrounds)
- **Scenarios:** Complete loan application via chat
- **Metrics:** Task completion rate, time on task, satisfaction score

---

## Deployment Strategy

### Phase 1 Deployment

- **Strategy:** Feature flag (internal testing first)
- **Rollout:** 10% → 50% → 100% over 1 week
- **Monitoring:** Intent accuracy, conversation length, error rate
- **Rollback:** Disable feature flag, revert to regex-based extraction

### Phase 2 Deployment

- **Strategy:** Beta program (selected users)
- **Rollout:** Internal → Beta users → General availability
- **Monitoring:** Document extraction accuracy, auto-population rate, STP trigger rate
- **Rollback:** Disable auto-processing, manual review mode

### Phase 3 Deployment

- **Strategy:** Gradual migration (parallel run)
- **Rollout:** New conversations use agentic flow, existing continue on old orchestrator
- **Monitoring:** Conversation naturalness, escalation rate, user satisfaction
- **Rollback:** Route all traffic to old orchestrator (30-day safety net)

---

## Monitoring & Observability

### Key Metrics to Track

| Metric | Source | Target | Alert Threshold |
|--------|--------|--------|-----------------|
| Intent Recognition Accuracy | LLM confidence scores | > 90% | < 80% |
| Conversation Turns to Snapshot | Conversation analytics | < 6 | > 10 |
| Document Extraction Accuracy | Extraction validation | > 85% | < 75% |
| STP Auto-Trigger Rate | STP processor logs | > 80% | < 60% |
| Response Time (p95) | Prometheus metrics | < 3s | > 5s |
| Escalation Rate | Escalation node logs | < 10% | > 20% |
| User Satisfaction | Post-conversation survey | > 4.0/5.0 | < 3.5/5.0 |

### Dashboards

- **Conversation Flow Dashboard:** Real-time conversation states, bottlenecks
- **Document Processing Dashboard:** Upload volume, extraction accuracy, processing time
- **STP Dashboard:** Auto-trigger rate, approval rate, checkpoint failures
- **Agent Performance Dashboard:** Response times, confidence scores, escalation rate

### Alerting

- **Critical:** LLM unavailable, STP processor failure, database errors
- **Warning:** Low intent accuracy, high escalation rate, slow response times
- **Info:** New conversation milestones, feature adoption metrics

---

## Success Criteria

### Phase 1 Success

- [ ] Intent recognition accuracy > 90% (measured on 100 test conversations)
- [ ] Average conversation turns to loan snapshot < 6
- [ ] Zero regression in existing functionality
- [ ] All unit tests passing (90%+ coverage)
- [ ] Manual QA sign-off on conversation naturalness

### Phase 2 Success

- [ ] Document field extraction accuracy > 85% (tested on 50 sample documents)
- [ ] Auto-population reduces manual entry by 50%
- [ ] STP auto-trigger rate > 80% (vs manual trigger baseline)
- [ ] Document processing time < 5 seconds average
- [ ] User satisfaction score > 4.0/5.0 (post-upload survey)

### Phase 3 Success

- [ ] Conversation naturalness score > 4.5/5.0 (user survey)
- [ ] Average conversation turns to completion < 8
- [ ] Escalation rate < 10% (most conversations handled by agent)
- [ ] Response time < 3 seconds (p95 latency)
- [ ] Zero critical bugs in production (first 30 days)
- [ ] Developer satisfaction > 4.0/5.0 (maintainability survey)

### Overall Project Success

- [ ] All three phases completed and deployed
- [ ] User completion rate increased by 30% (vs baseline)
- [ ] Support ticket volume reduced by 20% (fewer confused users)
- [ ] Officer time per application reduced by 40% (auto-processing)
- [ ] Regulatory audit passed with no findings
- [ ] System uptime > 99.9% (first 90 days post-deployment)

---

## Appendix A: LNAI Prompt Reference

### Key LNAI Patterns to Preserve

#### 1. Three-Mode Conversation Structure

```
Mode 1: Advisory (Understanding & Estimation)
  Step 1 → Understand the need (purpose, name)
  Step 2 → Employment & income
  Step 3 → Financial details (amount, debts)
  Step 4 → Loan snapshot + 3 recommendations (COMBINED)

Mode 2: Application (Collecting Remaining Details)
  Step 5 → Contact capture (email, phone)
  Step 6 → Submit application (all 10 fields)

Mode 3: Completion (Post-Submission)
  STP awareness
  Step 7 → Documents checklist
  Terms acceptance
  Disbursement
```

#### 2. XML Tag Output Format

```xml
<intent_analysis>
{
  "purpose": "Home purchase",
  "urgency": "medium",
  "monthlyIncome": "$8,000",
  "existingDebts": "Car loan $1,200/month",
  "loanAmount": "$400,000",
  "employmentType": "Salaried",
  "seriousnessScore": 75,
  "fitScore": 82
}
</intent_analysis>

<loan_snapshot>
{
  "loanType": "Home Loan",
  "loanAmount": "$400,000",
  "estimatedEmi": "$2,800/month",
  "tenure": "20 years",
  "rateBand": "7.5% – 9.5%",
  "ltv": "85%"
}
</loan_snapshot>

<loan_recommendations>
[
  {
    "name": "Home Purchase Loan — Fast Track",
    "type": "Home Loan (HL-PUR-001)",
    "estimatedRate": "7.5% - 8.5%",
    "estimatedEmi": "$3,200/month",
    "tenure": "15 years",
    "pros": ["Lowest total interest", "Faster payoff"],
    "cons": ["Highest monthly commitment"],
    "recommendation": "Best if you want to save on interest"
  }
]
</loan_recommendations>

<loan_application>
{
  "firstName": "Marcus",
  "lastName": "Williams",
  "email": "marcus.w@email.com",
  "phone": "+1-868-555-1234",
  "loanType": "Home Loan",
  "loanAmount": "$400,000",
  "purpose": "Purchase property in Port of Spain",
  "employmentType": "Salaried",
  "monthlyIncome": "$12,000",
  "existingDebts": "Vehicle loan $1,500/month"
}
</loan_application>

<documents_checklist>
{
  "requiredNow": [
    {"name": "Valid National ID", "description": "Government-issued photo ID"},
    {"name": "Job Letter", "description": "From current employer, < 3 months"}
  ]
}
</documents_checklist>
```

#### 3. Pacing Rules (Critical)

- **ONE INTENT PER TURN:** Never ask for multiple categories of information
- **NEVER combine:** Loan estimate + contact capture in one message
- **ALWAYS pair:** `<loan_snapshot>` + `<loan_recommendations>` together
- **NEVER submit application** until all 10 required fields collected
- **ALWAYS include** `<documents_checklist>` with submission

#### 4. Caribbean Regional Context

- Default currency: USD ($)
- Local currencies: TTD, JMD, BBD, GYD, BSD, XCD
- Employment types: Salaried, Self-Employed, Contractor
- Typical documents: National ID, Job Letter, Pay Slips, NIS Record
- Lending norms: Interest rates 5-12%, FOIR 40-45%, LTV 80-90%

---

## Appendix B: File Structure

### New Files to Create

```
src/
├── agents/
│   ├── structured_parser.py          # XML tag extraction
│   ├── prompts.py                    # System prompts (LNAI-style)
│   ├── graph_state.py                # Agentic state schema
│   ├── graph.py                      # LangGraph workflow definition
│   ├── tools/
│   │   ├── intent_extractor.py       # LLM-powered intent extraction
│   │   ├── document_requirements.py  # Checklist generation
│   │   └── product_matcher.py        # Catalog-based recommendations
│   └── nodes/
│       ├── advisory_node.py          # Mode 1: Understanding
│       ├── application_node.py       # Mode 2: Collection
│       ├── completion_node.py        # Mode 3: STP + disbursement
│       ├── document_processor_node.py # Auto-population from docs
│       ├── stp_trigger_node.py       # Auto-STP on threshold
│       ├── repair_node.py            # Conversation repair
│       ├── rag_node.py               # Policy-grounded responses
│       └── escalation_node.py        # Human handoff
├── core/
│   └── document_intelligence.py      # OCR + field extraction
└── tests/
    ├── test_structured_parser.py
    ├── test_intent_extractor.py
    ├── test_document_intelligence.py
    ├── test_agentic_workflow.py
    └── test_e2e_borrower_journey.py

frontend/
└── src/
    └── components/
        └── documents/
            └── DocumentUploadPanel.tsx  # Enhanced with extraction status
```

### Files to Modify

```
src/
├── agents/
│   └── orchestrator.py               # Add deprecation warnings, LLM integration
├── api/
│   └── routers/
│       └── v2_conversations_router.py # Route to agentic workflow
└── core/
    └── calculation_engines.py        # Integrate with advisory node
```

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **LLM** | Large Language Model (e.g., qwen2.5:7b, GPT-4) |
| **STP** | Straight-Through Processing (automated underwriting) |
| **RAG** | Retrieval-Augmented Generation (LLM + knowledge base) |
| **FOIR** | Fixed Obligation to Income Ratio (debt-to-income) |
| **LTV** | Loan-to-Value ratio (loan amount / property value) |
| **EMI** | Equated Monthly Installment (loan payment) |
| **OCR** | Optical Character Recognition (text extraction from images) |
| **LangGraph** | Graph-based workflow orchestration for LLM agents |
| **Pydantic** | Python data validation using type hints |
| **XML Tag Parsing** | Extracting structured JSON from XML-delimited blocks |

---

## Appendix D: Decision Log

| Date | Decision | Rationale | Owner |
|------|----------|-----------|-------|
| 2026-03-26 | Hybrid Phased Approach | Balance innovation with risk management; each phase delivers value | Development Team |
| 2026-03-26 | Preserve deterministic calculations | Financial accuracy cannot be LLM-approximated | Development Team |
| 2026-03-26 | Use Ollama (qwen2.5:7b) as primary LLM | Cost-effective, local deployment, already in KS-LOS stack | Development Team |
| 2026-03-26 | Port LNAI prompt patterns (not code) | LNAI's brilliance is in prompt engineering, not architecture | Development Team |
| TBD | [Future decisions] | [Rationale] | [Owner] |

---

## Progress Tracking

### Phase 1 Status

| Task | Owner | Start Date | End Date | Status | Notes |
|------|-------|------------|----------|--------|-------|
| 1.1 Structured Parser | | | | ⚪ Not Started | |
| 1.2 System Prompt | | | | ⚪ Not Started | |
| 1.3 Intent Tool | | | | ⚪ Not Started | |
| 1.4 Schema Enhancement | | | | ⚪ Not Started | |
| 1.5 Integration | | | | ⚪ Not Started | |
| 1.6 XML Response | | | | ⚪ Not Started | |
| 1.7 Tests | | | | ⚪ Not Started | |

### Phase 2 Status

| Task | Owner | Start Date | End Date | Status | Notes |
|------|-------|------------|----------|--------|-------|
| 2.1 Document Intelligence | | | | ⚪ Not Started | |
| 2.2 Requirements Tool | | | | ⚪ Not Started | |
| 2.3 Auto-Population | | | | ⚪ Not Started | |
| 2.4 STP Trigger | | | | ⚪ Not Started | |
| 2.5 Frontend UI | | | | ⚪ Not Started | |
| 2.6 Tests | | | | ⚪ Not Started | |

### Phase 3 Status

| Task | Owner | Start Date | End Date | Status | Notes |
|------|-------|------------|----------|--------|-------|
| 3.1 State Schema | | | | ⚪ Not Started | |
| 3.2 Advisory Node | | | | ⚪ Not Started | |
| 3.3 Application Node | | | | ⚪ Not Started | |
| 3.4 Completion Node | | | | ⚪ Not Started | |
| 3.5 Repair Node | | | | ⚪ Not Started | |
| 3.6 RAG Node | | | | ⚪ Not Started | |
| 3.7 Escalation Node | | | | ⚪ Not Started | |
| 3.8 Deprecation | | | | ⚪ Not Started | |
| 3.9 Tests | | | | ⚪ Not Started | |

---

## Review & Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Technical Lead | | | |
| Product Owner | | | |
| QA Lead | | | |
| Security Review | | | |
| Compliance Review | | | |

---

**Document Version:** 1.0  
**Next Review Date:** Weekly (every Monday)  
**Distribution:** Development Team, Stakeholders
