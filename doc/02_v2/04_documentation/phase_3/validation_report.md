# Phase 3 Validation Report (LOS v2)

## Validation Objective

Validate that the officer experience is operational and that workflow objects (conversations, loans, phases, products) behave consistently across the UI surfaces.

---

## Officer Dashboard Validation

- [ ] Conversations list shows real persisted leads
- [ ] Selecting a lead shows message history and extracted insights
- [ ] Status updates persist and reflect on refresh
- [ ] Assignment changes persist and reflect on refresh (if enabled)

---

## Pipeline Validation

- [ ] Phases render ordered by `sortOrder` and filtered by `isActive`
- [ ] Loans appear in the correct phase column by `currentPhaseId`
- [ ] Unassigned loans appear in the Unassigned column
- [ ] Loan detail patch persists and reflects after refetch

---

## Officer Lifecycle Chat Validation

- [ ] Officer-only actions are accepted only when authorized
- [ ] Action execution writes an audit event (action type + payload + result)
- [ ] Invalid actions are rejected with 400 and clear errors

---

## Exit Criteria

Phase 3 is accepted when:

- Integration tests pass for officer endpoints and authorization enforcement
- Playwright E2E officer flows pass
- Audit evidence exists for all state mutations

