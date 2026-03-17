# 08 — Shell Integration Plan (UI Parity + Functional Contract)

**Project:** KS-LOS v2 (LoanAssist AI / Loan Navigator)  
**Version:** 1.0  
**Purpose:** Systematically clone the Loan-Navigator-AI “shell” into the real LOS while ensuring every screen is backed by production-grade logic (agentic outputs + persistence + auditability + tests).  
**Source of Truth (Shell):** [/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)  
**Real App (LOS):** `/frontend` + `/src` (FastAPI + SQLAlchemy)  

---

## 1. Executive Summary

The UI in `/doc/02_Loan-Navigator-AI/client/src/pages` is not only a visual design; it encodes an operational product contract:

- Borrower chat is a workflow that advances phases and generates recommendations grounded in the product catalog.
- Officer experiences operationalize leads into loans and move them through a lifecycle with persistence and audit trails.
- “Agentic” behavior is not freeform chat; it must emit structured outputs that deterministically drive UI panels and workflow actions.

This plan defines a **view-by-view integration sequence** where each screen is considered complete only when:

- **UI parity** matches the shell layout and states (loading/empty/error/success).
- **Functional parity** matches the shell behavior, backed by real data and business rules.
- **Persistence** exists for all workflow entities (Conversation, Message, LoanPhase, Loan, CatalogProduct).
- **Auditability** exists for all writes (traceable and inspectable).
- **Regression tests** validate the user-visible behavior and the backend contracts.

---

## 2. Scope and Non-Goals

### 2.1 In Scope

- Pixel-by-pixel UI parity against the shell, screen by screen.
- Functional wiring to v2 APIs and database entities.
- Agentic/heuristic logic that produces stable structured outputs for the UI.
- Evidence-driven test suite (unit + integration + E2E) with deterministic seeding.

### 2.2 Non-Goals (for this plan)

- A final auth/RBAC model (header-gated officer access is acceptable in early phases).
- Performance tuning and full observability rollout beyond what is required for correctness and auditability.
- Replatforming frontend to the shell’s component library; parity may be achieved within the existing `/frontend` stack.

---

## 3. Guiding Principles (Contract Discipline)

- **UI is the contract:** the shell defines both layout and behavioral expectations.
- **Workflow-first objects:** Conversations and Loans are different entities; both must persist and be auditable.
- **Structured outputs only:** UI panels must be driven by typed metadata, not string parsing of assistant text.
- **Determinism at boundaries:** validations, phase transitions, actions, and permissions must be deterministic.
- **“Done” requires tests:** a screen is not “integrated” without passing regression coverage.

---

## 4. Current Baseline (What Exists Today)

### 4.1 LOS Routes Currently Implemented

- Borrower: `/` (BorrowerHomePage + borrower chat + phase tracker + insights)  
  Reference: [App.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/App.tsx)
- Officer: `/dashboard`, `/pipeline`, `/loan-products`, `/officer-chat`  
  Reference: [App.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/App.tsx#L1751-L1877)

### 4.2 v2 Backend Endpoints Currently Implemented

- Conversations + messages: [v2_conversations_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_conversations_router.py)
  - `POST /api/conversations`
  - `GET /api/conversations` (officer-only)
  - `GET /api/conversations/{id}`
  - `PATCH /api/conversations/{id}` (officer-only)
  - `GET /api/conversations/{id}/messages`
  - `POST /api/conversations/{id}/messages`
- Phases: [v2_phases_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_phases_router.py)
  - `GET /api/phases`
  - `GET /api/phases/active`
  - `GET /api/phases/{id}/detail`
  - `POST /api/phases/actions` (officer-only)
- Loans: [v2_loans_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_loans_router.py) (officer-only)
  - `GET /api/loans`
  - `GET /api/loans/{id}`
  - `POST /api/loans`
  - `PATCH /api/loans/{id}`
  - `PATCH /api/loans/{id}/documents`
  - `GET /api/loans/{id}/underwriting-memo`
  - `POST /api/loans/{id}/underwriting-memo`
  - `POST /api/loans/actions`
- Catalog products: [v2_catalog_products_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_catalog_products_router.py) (officer-only)
  - `GET /api/catalog-products`
  - `POST /api/catalog-products`
  - `PATCH /api/catalog-products/{id}`

### 4.3 Borrower Chat Functional Baseline (Recent Hardening)

- Assistant reply is context-sensitive and derived from extracted intent fields.
- Debt consolidation routes to personal-loan recommendations.
- E2E assertions validate: user message, assistant reply, next angle populated, recommendations visible.  
  Reference: [chat_config.spec.ts](file:///Users/albertohernandez/Documents/projects/ks-los/e2e/tests/chat_config.spec.ts)

---

## 5. Shell → LOS Integration Map (Views + Functionalities)

### 5.1 View Parity Matrix (Primary Contract)

| Shell View (Source) | Shell Route | LOS Route | Functional Contract (What must work) | Data + APIs (LOS) | Required Tests | Status |
|---|---:|---:|---|---|---|---|
| Borrower Chat ([chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/chat.tsx)) | `/` | `/` | Create conversation, send messages, update phase tracker, show recommendations + insights | `/api/conversations*`, `/api/phases/active` | E2E borrower chat happy path + backend integration | **Implemented (baseline)** |
| Officer Dashboard ([officer-dashboard.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-dashboard.tsx)) | `/dashboard` | `/dashboard` | List leads, view details/history, update status + assignment, show seriousness/fit/next angle | `/api/conversations` + PATCH | E2E officer lead edit persists + integration auth tests | **Implemented (baseline)** |
| Loan Pipeline ([loan-pipeline.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-pipeline.tsx)) | `/pipeline` | `/pipeline` | Group loans by phase, unassigned bucket, open loan detail, persist edits | `/api/loans`, `/api/phases` | E2E grouping + patch persist + integration | **Implemented (baseline)** |
| Product Catalog ([loan-products.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-products.tsx)) | `/loan-products` | `/loan-products` | List products, create/edit products, required docs drive checklist logic | `/api/catalog-products` | E2E create/edit + backend integration | **Implemented (baseline)** |
| Officer Lifecycle Chat ([officer-chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-chat.tsx)) | `/officer-chat` | `/officer-chat` | Officer chat session that triggers validated actions and refreshes pipeline/loans | `/api/conversations` (officer), `/api/loans/actions`, `/api/phases/actions` | E2E: officer action → loan created/updated | **Implemented (baseline)** |
| Phase Detail ([phase-detail.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/phase-detail.tsx)) | `/phases/:id` | `/phases/:id` | View phase knowledge + metrics and link back; phase id is stable | `/api/phases`, `/api/phases/{id}/detail` | E2E: open phase detail from tracker | **Implemented (baseline)** |

### 5.2 Functional Parity Matrix (Behavior-Level Contract)

These are the “non-negotiable” functional behaviors that must be identical to the shell semantics (even if implementation differs).

#### Borrower Chat

- **Conversation lifecycle**
  - Create conversation initializes persisted state and greeting message.
  - Conversation ID is stored client-side for continuity (refresh safe).
- **Message semantics**
  - Each send persists both user and assistant messages.
  - Assistant returns structured metadata used by UI panels.
- **Phase semantics**
  - Borrower phases are sequential; no skipping.
  - Phase changes are persisted on the conversation.
- **Recommendations**
  - Recommendations are derived from the product catalog (not hardcoded).
  - Recommendations update as intent becomes more complete.
- **Insights**
  - Seriousness score + fit score + next conversation angle are persisted and displayed.
  - Approval probability is deterministic and bounded.

#### Officer Dashboard

- **Lead visibility**
  - Lead list is officer-only and includes the newest conversations first.
  - Lead cards show key extracted values when available.
- **Lead operations**
  - Officer can update `status`, `borrowerName`, `assignedOfficer`, and `currentPhaseId`.
  - Updates persist and are visible after refresh.
- **Audit**
  - All mutations emit audit events with correlation-friendly metadata.

#### Product Catalog

- **Catalog as authority**
  - Product definitions are the authority for: recommendation selection and required document lists.
  - Edits affect downstream recommendations and checklist generation.

#### Loan Pipeline

- **Loan as workflow artifact**
  - Loans persist independently of chat messages.
  - Loans appear in the correct phase column based on `currentPhaseId`.
- **Document checklist**
  - Checklist is derived from product requirements and persists per-loan.
  - Document statuses update via an explicit API and are auditable.

#### Officer Lifecycle Chat

- **Action execution (agentic boundary)**
  - Officer chat can trigger validated actions that mutate loans/phases.
  - Actions are schema-validated and permission-gated.
  - UI must render “action results” (success/failure) deterministically.

---

## 6. Execution Sequence (View-by-View)

This is the strict order of integration to minimize dependency churn.

### Step 1 — Borrower Chat (Lock Contract)

- Freeze the borrower chat contract: required metadata fields and UI expectations.
- Expand deterministic extraction and scoring only when it produces stable UI state.
- Required regression:
  - Borrower quick prompt → assistant reply → tracker visible → recommendations visible.
  - “Next Conversation Angle” becomes non-empty.

### Step 2 — Officer Dashboard (Operational Lead Management)

- Ensure lead list + lead detail parity with shell.
- Confirm officer edits are persisted and audited.
- Ensure detail panel includes the same “insight surfaces” as shell (scores, intent fields, recommended products).

### Step 3 — Product Catalog (Authority for Recommendations + Documents)

- Ensure create/edit flows are complete and persist correctly.
- Ensure required documents impact checklist generation for newly created loans.

### Step 4 — Loan Pipeline (Loans as Work Items)

- Ensure phase grouping is correct and stable.
- Ensure loan patching and document status updates are audit-backed and refresh-safe.

### Step 5 — Officer Lifecycle Chat (Agentic Operations)

- Implement a strict “action contract” the officer chat can trigger:
  - Create/update loans (`/api/loans/actions`)
  - Add/reorder/activate phases (`/api/phases/actions`)
- Ensure each action yields: success/failure payload + UI-renderable result.

### Step 6 — Phase Detail (Knowledge + Metrics)

- Add the missing LOS route and page for phase detail parity.
- Wire to `/api/phases` and add any derived metrics needed by the shell behavior.

---

## 7. Dependencies and Integration Constraints

### 7.1 Hard Dependencies (Must exist first)

- Seeded baseline phases and products must be deterministic for E2E.
- Officer-only endpoints must enforce access at the API boundary.
- UI must not depend on undefined fields; every new field requires contract updates and tests.

### 7.2 Soft Dependencies (Can be incremental)

- Advanced agentic behaviors (RAG, memo generation, next-best-action) can be phased in after contract stability.
- Auth upgrade to RBAC can be deferred until workflows are stable.

---

## 8. Test Strategy (Evidence Requirements)

### 8.1 Test Pyramid (Minimum Required Per View)

- **Unit tests**
  - Extraction/scoring/action validators: deterministic rules and schema validation.
- **Integration tests (FastAPI)**
  - Endpoint contract: status codes, payload shape, persistence, auth boundary.
- **E2E tests (Playwright)**
  - User-visible flows per route + key invariants (no broken chat, no missing panels, refresh-safe).

### 8.2 Deterministic Seeds

- E2E must run from a reset baseline with idempotent seeding.
- Tests must not rely on “environment luck” (random ordering, stale localStorage, etc.).

### 8.3 “Stop-the-line” Regressions

- Borrower cannot send/receive chat messages.
- Recommendations render but are not derived from persisted catalog products.
- Phase tracker displays a phase that does not match persisted state.
- Officer endpoints allow unauthorized access.

---

## 9. Acceptance Criteria (Definition of Done)

### 9.1 Per-View Acceptance Gate

A view is accepted only when all are true:

- UI matches the shell layout and states.
- Functional behaviors match the shell semantics (Section 5.2).
- All reads/writes go through v2 endpoints; no hardcoded demo data.
- Writes are auditable (audit event present).
- Required unit + integration + E2E tests pass in CI.

### 9.2 Global Acceptance Gate (Release-Ready)

- Full E2E regression suite passes deterministically.
- All workflow entities (Conversation/Message/Loan/Phase/Product) are persisted and consistent.
- Agent outputs used by UI are schema-validated and backwards compatible.

---

## 10. Status Tracking (Work Package Alignment)

This document aligns with the v2 work packages in: [02_work_packages.md](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_v2/02_work_packages.md)

- **Implemented (baseline):** WP-V2-001 .. WP-V2-012 (route set + core APIs + borrower workflow + pipeline baseline)
- **Implemented (baseline):** WP-V2-013 .. WP-V2-014 (officer lifecycle chat action semantics)
- **Implemented (incremental):** WP-V2-015 .. WP-V2-017 (probability navigator, checklist baseline, underwriting memo)
- **Implemented (Phase 5 incremental):** WP-V2-018 (RBAC auth boundary + authorization tests)
- **Implemented (Phase 5 incremental):** WP-V2-019 (audit coverage + v2 funnel metrics + evidence tests)
- **Planned (Phase 5 hardening):** WP-V2-020 (deterministic regression hardening)

---

## 11. Risks and Mitigations

- **Risk: UI parity without contract parity**
  - Mitigation: per-view acceptance gate requires E2E + backend integration tests before sign-off.
- **Risk: Agent output instability breaks UI**
  - Mitigation: structured outputs only; schema validation; tolerant checks for freeform text fields; contract versioning discipline.
- **Risk: Catalog edits break recommendations/checklists**
  - Mitigation: integration tests that verify derived behaviors when products change.
- **Risk: Non-deterministic test data**
  - Mitigation: reset-based seed endpoint and localStorage cleanup in E2E.
