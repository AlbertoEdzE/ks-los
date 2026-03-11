# Work Packages (LOS v2)

**Version:** 1.0  
**Purpose:** Translate the v2 plan into executable work packages with test evidence requirements.  
**Source of Truth:** [/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## Conventions

- IDs use the format `WP-V2-XXX`.
- Every work package must define:
  - UI linkage (which page/flow)
  - API contract impact
  - Data model impact
  - Test evidence (unit/integration/e2e)
- A work package is “Done” only when its tests pass and the phase report is updated.

---

## Phase 1 — UI Wiring + Product API Skeleton

### WP-V2-001 — Bootstrap v2 frontend with Loan Navigator route set

- UI linkage: borrower chat `/`, officer dashboard `/dashboard`, pipeline `/pipeline`, products `/loan-products`, officer chat `/officer-chat`
- Acceptance:
  - All routes render without console errors
  - Navigation between routes matches the UI design
- Test evidence:
  - E2E: smoke navigation test across all routes

### WP-V2-002 — Implement conversations endpoints (create/list/get/patch)

- API linkage: `/api/conversations` and `/api/conversations/:id`
- Data impact: `conversations` table/entity
- Acceptance:
  - Create returns a conversation and greeting payload
  - List returns conversations for officer only
  - Patch updates status/assignment/currentPhaseId for officer only
- Test evidence:
  - Integration: CRUD + auth coverage

### WP-V2-003 — Implement messages endpoints (list/send)

- API linkage: `/api/conversations/:id/messages`
- Data impact: `messages` table/entity (metadata JSON)
- Acceptance:
  - Send persists both user and assistant messages
  - List returns full history ordered by createdAt
- Test evidence:
  - Integration: list/send behavior
  - E2E: borrower can send message and see assistant reply

### WP-V2-004 — Implement phases endpoints (all + active)

- API linkage: `/api/phases`, `/api/phases/active`
- Data impact: `loan_phases` table/entity
- Acceptance:
  - Active phases return ordered by sortOrder
  - UI phase tracker renders when phases exist
- Test evidence:
  - Integration: list/active endpoints
  - E2E: borrower chat shows phase tracker

### WP-V2-005 — Implement loans endpoints (officer list + patch)

- API linkage: `/api/loans`, `/api/loans/:id`
- Data impact: `loans` table/entity
- Acceptance:
  - Officer can list loans
  - Officer can patch loan fields and see changes persist
- Test evidence:
  - Integration: list/patch + auth
  - E2E: pipeline shows loans and patch persists after refresh

### WP-V2-006 — Implement catalog products endpoints (officer CRUD)

- API linkage: `/api/catalog-products` and `/api/catalog-products/:id`
- Data impact: `loan_product_catalog` table/entity
- Acceptance:
  - Officer can list/create/patch products
  - Product page can render seeded and newly created products
- Test evidence:
  - Integration: list/create/patch + auth
  - E2E: create/edit product flows

### WP-V2-007 — Add deterministic seed routines (phases + products)

- Acceptance:
  - Seed is idempotent (can run repeatedly without duplication)
  - UI renders stable demo data
- Test evidence:
  - Integration: seed endpoint behavior (or seed script behavior)
  - E2E: tests rely on seeded baseline

---

## Phase 2 — Borrower Workflow Semantics

### WP-V2-008 — Persist intent summary and lead scores on message send

- UI linkage: borrower chat and officer dashboard lead scoring
- Acceptance:
  - Conversation fields populate: intentSummary, seriousnessScore, fitScore, nextConversationAngle
- Test evidence:
  - Unit: schema validation for intent payload
  - Integration: message send updates conversation

### WP-V2-009 — Implement borrower phase progression guardrails

- UI linkage: borrower phase tracker
- Acceptance:
  - Borrower phase changes are sequential and validated
  - Phase does not skip stages
- Test evidence:
  - Unit: transition rules
  - Integration: message send can advance phase only when allowed

### WP-V2-010 — Implement product-driven recommendations payload

- UI linkage: borrower chat recommendation cards and officer lead detail
- Acceptance:
  - recommendedProducts derived from catalog products, not hardcoded
- Test evidence:
  - Unit: recommendation selection rules
  - Integration: recommendations persist on conversation

---

## Phase 3 — Officer Workflow

### WP-V2-011 — Officer dashboard: lead detail mutations

- UI linkage: officer dashboard lead detail
- Acceptance:
  - Officer can update conversation status and assignment; persists on refresh
- Test evidence:
  - Integration: PATCH conversation (auth enforced)
  - E2E: dashboard update flow

### WP-V2-012 — Pipeline: unassigned loans and phase grouping

- UI linkage: pipeline board
- Acceptance:
  - Unassigned column behavior matches UI expectations
  - Grouping by currentPhaseId is correct
- Test evidence:
  - Integration: loan list and phase list consistency
  - E2E: pipeline grouping assertions

### WP-V2-013 — Officer lifecycle chat: validated loan actions

- UI linkage: officer-chat
- Acceptance:
  - Officer chat can create/update loans via validated action payloads
  - All actions produce audit records
- Test evidence:
  - Unit: action validator
  - Integration: action execution

### WP-V2-014 — Officer lifecycle chat: validated phase actions

- UI linkage: officer-chat + pipeline
- Acceptance:
  - Officer can add/reorder/deactivate/reactivate phases via chat actions
  - Pipeline reflects changes
- Test evidence:
  - Unit: phase action validator
  - Integration: phase action execution

---

## Phase 4 — Agentic Features

### WP-V2-015 — Approval probability navigator (likelihood + blockers + next actions)

- UI linkage: borrower and officer insight surfaces
- Acceptance:
  - Outputs are schema-validated and persisted
  - Next actions are actionable and consistent with constraints
- Test evidence:
  - Unit: schema validation + bounds
  - Integration: surfaces read persisted outputs

### WP-V2-016 — Document checklist baseline (product-driven)

- Acceptance:
  - Required documents derived from catalog products
  - Loan has document state tracking
- Test evidence:
  - Unit: checklist rules
  - Integration: checklist persistence

### WP-V2-017 — Underwriting memo artifact + guardrails

- Acceptance:
  - Memo is generated with required sections and evidence links
  - Guardrails prevent promises and non-compliant outputs
- Test evidence:
  - Unit: memo schema + guardrail rule tests
  - Integration: memo persistence/retrieval

---

## Phase 5 — Hardening

### WP-V2-018 — Upgrade auth boundary to RBAC

- Acceptance:
  - Borrower/officer roles enforced without relying on static header token
- Test evidence:
  - Unit + integration: authorization tests

### WP-V2-019 — Observability completeness (audit + metrics)

- Acceptance:
  - All writes emit audit events; key metrics exist for funnel and performance
- Test evidence:
  - Integration: audit event checks and metrics endpoint checks

### WP-V2-020 — Full Playwright regression suite stabilization

- Acceptance:
  - Deterministic seeds + stable test fixtures
  - Full suite passes reliably on CI
- Test evidence:
  - CI artifacts show green regression runs

---

## Phase 6 — CI/CD + Security + Performance Gates

### WP-V2-021 — CI pipelines with required gates and artifacts

- Acceptance:
  - Lint/typecheck/unit/integration/e2e run per policy
  - Reports uploaded

### WP-V2-022 — Security scanning gates (secrets + dependencies)

- Acceptance:
  - Secrets scanning and dependency audit are enforced and block merges

### WP-V2-023 — Performance baseline scripts and regression thresholds

- Acceptance:
  - Baselines exist for key endpoints and regressions are gated

---

## Phase 7 — Go-Live, Governance & Ethics

### WP-V2-024 — Governance: approval workflows and audit retention

- Acceptance:
  - Policy/catalog changes follow approvals and are reviewable with retention

### WP-V2-025 — Fairness/drift checks as release gates

- Acceptance:
  - Bias/parity and drift checks are repeatable and enforced for releases

### WP-V2-026 — Operational runbooks and rollback drills

- Acceptance:
  - Incident response and rollback procedures exist and are validated by a drill

