# Version Control Setup (LOS v2)

**Document ID:** VCS-V2-001  
**Version:** 1.0  
**Phase:** 0.3  
**Status:** Draft  
**Last Updated:** March 2026

---

## 1. Purpose and Scope

This document defines the version control practices for KS LOS v2. It mirrors the rigor established in v1 execution documentation while adapting the branch taxonomy and ownership boundaries to the v2 product surfaces (borrower UI, officer UI, product API, agent core).

The primary objective is traceability: each change must be attributable to a work package and verified by tests appropriate to the impacted surface.

---

## 2. Repository Structure (Target)

The repository should preserve a clear separation between:

- Frontend (Loan Navigator UI implementation)
- Backend (product API, persistence, auth, audit)
- Agent core (structured outputs, decisioning, guardrails)
- E2E test suite (Playwright)

---

## 3. Branching Strategy

### 3.1 Branch Types

- `main`: protected, always releasable
- `feat/*`: feature work branches
- `fix/*`: bugfix branches
- `phase-<N>/*`: milestone/integration branches for phase stabilization
- `release/*`: tagged release preparation (optional)

### 3.2 Domain Prefixes (Recommended)

To support parallel work without conflicts, use a prefix after the type:

| Domain | Prefix | Examples |
|--------|--------|----------|
| Frontend | `frontend/` | `feat/frontend/borrower-chat-phase-tracker` |
| Backend API | `backend/` | `feat/backend/conversations-endpoints` |
| Data/Persistence | `data/` | `feat/data/migrations-loans-phases` |
| Agent Core | `agent/` | `feat/agent/intent-summary-validator` |
| E2E | `e2e/` | `feat/e2e/borrower-flow-smoke` |
| Infra/CI | `infra/` | `feat/infra/ci-playwright` |

---

## 4. Commit Conventions

### 4.1 Message Format

Follow:

`<type>(<scope>): <imperative description>`

Examples:

- `feat(backend): implement conversations CRUD endpoints`
- `fix(frontend): stabilize phase tracker rendering on refresh`
- `test(e2e): add borrower welcome-to-chat smoke test`

### 4.2 Work Package References

Every commit should reference a work package ID in the body:

`[WP-V2-XXX] <short summary>`

---

## 5. Branch Protection and Quality Gates

Main branch protection requires:

- Pull request reviews (minimum 1; 2 for security/auth or decisioning logic)
- CI status checks passing:
  - lint
  - typecheck
  - unit tests
  - integration tests
  - Playwright E2E (phase-dependent gating)
- No unresolved PR conversations

---

## 6. Release Tagging

- Tag releases as `v2.<minor>.<patch>` when acceptance gates are met.
- Phase completion tags may be used as `v2-phase-<N>` for demo checkpoints.

