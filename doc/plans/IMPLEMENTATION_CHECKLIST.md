# Agentic Orchestrator Implementation Checklist

**Quick Reference for Daily Standups**

---

## Phase 1: LLM-Powered Intent Extraction (Weeks 1-2)

### Week 1

- [ ] **1.1** Create `src/agents/structured_parser.py`
  - [ ] XML tag extraction regex patterns
  - [ ] JSON normalization (fix quotes, remove markdown)
  - [ ] Pydantic validation for each tag type
  - [ ] Graceful fallback on parse failures
  - [ ] Unit tests (100% coverage for parser)

- [ ] **1.2** Create `src/agents/prompts.py`
  - [ ] Port LNAI borrower system prompt
  - [ ] Add KS-LOS specific elements (STP, RAG)
  - [ ] Define XML output format instructions
  - [ ] Test prompt with Ollama (qwen2.5:7b)

- [ ] **1.3** Create `src/agents/tools/intent_extractor.py`
  - [ ] LangChain ToolNode-compatible tool
  - [ ] Ollama integration
  - [ ] Confidence scoring per field
  - [ ] Pydantic output schema

- [ ] **1.4** Enhance `src/agents/orchestrator.py` schemas
  - [ ] Add LNAI fields to CapturedContext
  - [ ] Add confidence scores
  - [ ] Add currency tracking
  - [ ] Add validation rules

### Week 2

- [ ] **1.5** Integrate LLM extraction into orchestrator
  - [ ] Replace regex in `_handle_intent_capture()`
  - [ ] Replace regex in `_handle_financial_context()`
  - [ ] Add confidence-based fallback logic
  - [ ] Integration tests

- [ ] **1.6** Add XML tag response generation
  - [ ] `<loan_snapshot>` generation
  - [ ] `<loan_recommendations>` generation
  - [ ] `<documents_checklist>` generation
  - [ ] `<loan_application>` generation
  - [ ] Frontend integration test

- [ ] **1.7** Create Phase 1 test suite
  - [ ] Parser tests
  - [ ] Intent extraction tests
  - [ ] Conversation flow tests
  - [ ] Error handling tests
  - [ ] Achieve 90%+ coverage

---

## Phase 2: Document Intelligence & Auto-Processing (Weeks 3-4)

### Week 3

- [ ] **2.1** Create `src/core/document_intelligence.py`
  - [ ] OCR with Tesseract
  - [ ] Document type classification
  - [ ] Field extraction per document type
  - [ ] Confidence scoring
  - [ ] Validation against user-declared info

- [ ] **2.2** Create `src/agents/tools/document_requirements.py`
  - [ ] Port LNAI getDocumentCategories() logic
  - [ ] Support loan type variations
  - [ ] Support employment type variations
  - [ ] Return DocumentsChecklist model

- [ ] **2.3** Create `src/agents/nodes/document_processor_node.py`
  - [ ] Listen for document upload events
  - [ ] Run Document Intelligence extraction
  - [ ] Auto-populate CapturedContext fields
  - [ ] Flag discrepancies

### Week 4

- [ ] **2.4** Create `src/agents/nodes/stp_trigger_node.py`
  - [ ] Define minimum document thresholds
  - [ ] Monitor upload progress
  - [ ] Auto-trigger STP when threshold met
  - [ ] Notify user

- [ ] **2.5** Enhance frontend DocumentUploadPanel.tsx
  - [ ] Display context-aware checklist
  - [ ] Show extraction progress
  - [ ] Display auto-populated fields
  - [ ] Show discrepancy warnings

- [ ] **2.6** Create Phase 2 test suite
  - [ ] OCR extraction tests
  - [ ] Document classification tests
  - [ ] Auto-population tests
  - [ ] STP trigger tests
  - [ ] Achieve 90%+ coverage

---

## Phase 3: Full Agentic Flow (Weeks 5-7)

### Week 5

- [ ] **3.1** Create `src/agents/graph_state.py`
  - [ ] Define AgenticOrchestratorState
  - [ ] Include all LNAI fields
  - [ ] Support conversation mode tracking
  - [ ] Pydantic validation

- [ ] **3.2** Create `src/agents/nodes/advisory_node.py`
  - [ ] Implement LNAI Mode 1 (4 steps)
  - [ ] LLM response generation
  - [ ] ONE INTENT PER TURN enforcement
  - [ ] XML tag output

- [ ] **3.3** Create `src/agents/nodes/application_node.py`
  - [ ] Implement LNAI Mode 2 (contact + submit)
  - [ ] Validate 10 required fields
  - [ ] Generate XML tags
  - [ ] Create loan record

### Week 6

- [ ] **3.4** Create `src/agents/nodes/completion_node.py`
  - [ ] Implement LNAI Mode 3
  - [ ] STP progress communication
  - [ ] Terms acceptance guidance
  - [ ] Disbursement confirmation

- [ ] **3.5** Create `src/agents/nodes/repair_node.py`
  - [ ] Detect user corrections
  - [ ] Detect digressions
  - [ ] Handle contradictions
  - [ ] Graceful recovery

- [ ] **3.6** Create `src/agents/nodes/rag_node.py`
  - [ ] Retrieve policies from PGVector
  - [ ] Ground LLM responses
  - [ ] Handle policy questions
  - [ ] Add citations

### Week 7

- [ ] **3.7** Create `src/agents/nodes/escalation_node.py`
  - [ ] Monitor confidence scores
  - [ ] Define escalation thresholds
  - [ ] Create officer handoff
  - [ ] Notify officers

- [ ] **3.8** Deprecate old orchestrator
  - [ ] Add deprecation warnings
  - [ ] Redirect API calls to LangGraph
  - [ ] Update documentation
  - [ ] Migration guide

- [ ] **3.9** Create Phase 3 test suite
  - [ ] Advisory mode tests
  - [ ] Application mode tests
  - [ ] Completion mode tests
  - [ ] Repair mechanism tests
  - [ ] E2E conversation tests
  - [ ] Achieve 90%+ coverage

---

## Definition of Done (Per Task)

- [ ] Code implemented
- [ ] Unit tests written (90%+ coverage)
- [ ] Integration tests pass
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff/flake8)
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Merged to main branch

---

## Progress Summary

| Phase | Total Tasks | Completed | In Progress | Not Started | % Done |
|-------|-------------|-----------|-------------|-------------|--------|
| Phase 1 | 7 | 0 | 0 | 7 | 0% |
| Phase 2 | 6 | 0 | 0 | 6 | 0% |
| Phase 3 | 9 | 0 | 0 | 9 | 0% |
| **Total** | **22** | **0** | **0** | **22** | **0%** |

---

**Last Updated:** 2026-03-26  
**Next Update:** Daily (end of each workday)
