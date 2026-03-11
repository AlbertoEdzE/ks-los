# Master Plan: LOS v2 Execution Checklist (Source-of-Truth: Loan-Navigator-AI)

**Project:** KS LOS v2 (LoanAssist AI / Loan Navigator)  
**Version:** 1.0  
**Purpose:** Phase-gated plan executed with scientific rigor, tests, and validation  
**Source of Truth (UI + implied contracts):** [/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## Guiding Principles

- **UI is the contract.** The end-state must match `/doc/02_Loan-Navigator-AI` behavior and layout.
- **Workflow-first.** Conversation, phases, loans, and product catalog are first-class entities.
- **Structured outputs.** Assistant responses must include validated metadata for UI panels and automation.
- **Deterministic guardrails.** Compliance-safe language and no false promises; everything is auditable.
- **Test-first integration.** Each phase ends with unit + integration + Playwright E2E coverage and a validation report.

---

## Phase 0: Foundation Setup (Pre-Development)

### 0.1 Ontology and Contracts
- [ ] Define v2 domain entities: Conversation, Message, LoanPhase, Loan, CatalogProduct
- [ ] Define role model: borrower vs officer; access enforcement at API boundary
- [ ] Define assistant structured metadata payloads required by UI
- [ ] Freeze v2 API surface aligned to the UI routes used in `/doc/02_Loan-Navigator-AI/client`

### 0.2 Work Breakdown Structure (WBS)
- [ ] Decompose work into phases, milestones, deliverables, tasks, test artifacts
- [ ] Define phase entry/exit criteria and acceptance gates
- [ ] Define the test pyramid requirements for each phase

### 0.3 Version Control Setup
- [ ] Repository branching strategy and branch protection
- [ ] Commit conventions and traceability rules (work package IDs)
- [ ] CI quality gates (lint, typecheck, unit tests, integration tests, e2e)

### 0.4 Issue Tracking Setup
- [ ] Epics map to phases; stories map to UI routes and backend capabilities
- [ ] Templates enforce: acceptance criteria, API impacts, schema impacts, tests, and rollout notes

---

## Phase 1: Target UI Wiring + Product API Skeleton

**Objective:** The UI pages from `/doc/02_Loan-Navigator-AI/client` run against a real backend contract (even if initially stubbed).

### 1.1 Frontend Baseline (Design-Exact)
- [ ] Bootstrap frontend with the same routing and pages as Loan Navigator
- [ ] Ensure theme toggle, navigation, and layout match the design
- [ ] Wire data fetching calls to the v2 backend base URL

### 1.2 Backend API Skeleton (Contract-Complete)
- [ ] Implement the core endpoints required by the UI:
  - Conversations: create, list, get, messages list, send message
  - Phases: list, active list
  - Loans: list (officer), patch/update (officer)
  - Catalog Products: list/create/update/activate/deactivate (officer)
- [ ] Implement officer authorization boundary (header-based for POC; extensible)
- [ ] Implement correlation IDs, audit log events, and structured error envelopes

### 1.3 Persistence Baseline
- [ ] Create schema migrations for conversations/messages/phases/loans/catalog products
- [ ] Seed minimal default loan phases and demo products
- [ ] Ensure idempotent seeding for repeatable demos and E2E tests

### 1.4 Testing and Validation Gate
- [ ] Unit tests: schema validation and core domain logic
- [ ] Integration tests: API contract behavior for each endpoint
- [ ] E2E tests: UI loads each page and renders empty/seeded states
- [ ] Produce Phase 1: test report, validation report, integration notes

---

## Phase 2: Borrower Experience (Chat + Phase Progress + Recommendations)

**Objective:** Borrower chat becomes a persisted workflow that advances phases and yields product recommendations.

### 2.1 Conversation Intelligence Outputs (Structured)
- [ ] Intent summary extraction aligned to UI expectations
- [ ] Seriousness score + fit score generation and persistence
- [ ] Recommended products payload generation and persistence

### 2.2 Phase Progression Logic
- [ ] Define allowed phase transitions for borrower chat
- [ ] Persist currentPhaseId and enforce sequential progression
- [ ] Render phase tracker updates in the UI

### 2.3 Recommendations Surface
- [ ] Generate recommendation cards from catalog + borrower intent
- [ ] Provide “why this product” and “next step” outputs usable by UI

### 2.4 Testing and Validation Gate
- [ ] Unit tests: intent schema, scoring rules, phase transition guard
- [ ] Integration tests: message send updates conversation metadata correctly
- [ ] E2E tests: borrower flow from welcome → chat → phase progress update
- [ ] Produce Phase 2: test report, validation report, e2e report

---

## Phase 3: Officer Experience (Dashboard + Pipeline + Lifecycle Chat)

**Objective:** Officer can operationalize leads into loans and move them through phases with auditability.

### 3.1 Officer Dashboard
- [ ] Conversations list refreshes and shows seriousness/fit summaries
- [ ] Conversation detail panel shows message history and extracted insights
- [ ] Officer assignment and status transitions (active/reviewing/qualified/archived)

### 3.2 Pipeline (Loan Artifact)
- [ ] Create/update loan records (from officer chat or dashboard)
- [ ] Phase-based pipeline board reflects loans by currentPhaseId
- [ ] Loan detail panel patch fields and persist updates

### 3.3 Officer Lifecycle Chat
- [ ] Officer chat role: can trigger loan actions (create/update) and phase actions (add/reorder/deactivate)
- [ ] Validate and restrict actions to officer authorization boundary

### 3.4 Testing and Validation Gate
- [ ] Integration tests: officer-only endpoints reject borrower requests
- [ ] E2E tests: dashboard → pipeline → loan detail patch persists
- [ ] Produce Phase 3: test report, validation report

---

## Phase 4: Agentic “Wow Features” (Probability Navigator, Completion, Underwriting)

**Objective:** Implement the five core v2 capabilities as first-class workflow outputs.

### 4.1 Approval Probability Navigator
- [ ] Approval likelihood score + top blockers + next best actions
- [ ] Counterfactual “what-if” support for amount/tenure/product changes

### 4.2 Autonomous Application Completion
- [ ] Checklist engine: required documents by product/segment
- [ ] Document state tracking and mismatch detection rules
- [ ] Reminder/escalation events and audit trail

### 4.3 Explainable Underwriting Copilot
- [ ] Underwriting memo schema with citations to evidence
- [ ] Policy + catalog-aware conditions and compensating factors
- [ ] Guardrails: compliance-safe messaging and no promises

### 4.4 Testing and Validation Gate
- [ ] Unit tests: checklist rules, scoring determinism, memo schema validity
- [ ] Integration tests: lifecycle actions create consistent audit events
- [ ] E2E tests: officer sees probability/blockers and recommended actions
- [ ] Produce Phase 4: validation report and drift/quality artifacts (as applicable)

---

## Phase 5: Hardening + Scientific Rigor (Reliability, Security, Observability)

**Objective:** Production-grade behaviors: resilience, security controls, monitoring, and reproducible evaluation.

### 5.1 Security and Compliance
- [ ] Authentication strategy upgrade (beyond header token) and RBAC
- [ ] PII minimization, retention policy, and auditability
- [ ] Prompt injection hardening and tool/action constraints

### 5.2 Observability
- [ ] Metrics for funnel conversion, drop-off points, phase time-in-stage
- [ ] Traceability from message → extracted intent → action → state change

### 5.3 Regression Suite
- [ ] Full Playwright suite executed on CI
- [ ] Golden test datasets for agent outputs and deterministic validation
- [ ] Release checklist and acceptance gate

