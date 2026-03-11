# Phase 4 Test Report (LOS v2)

## Scope

Phase 4 testing validates:

- Approval probability navigator output stability and persistence
- Blockers and next-best-actions determinism where required
- Document checklist generation aligned to product catalog constraints
- Underwriting memo schema correctness and guardrail enforcement

---

## Unit Tests

- [ ] Approval likelihood computation produces bounded outputs (0–100)
- [ ] Blocker extraction schema validation
- [ ] Next-best-actions schema validation
- [ ] Checklist rules: required docs derived from product config
- [ ] Underwriting memo schema validation
- [ ] Guardrails reject disallowed claims/promises

---

## Integration Tests

- [ ] Borrower message triggers updated probability + blockers in conversation fields
- [ ] Officer views probability/blockers surfaces for a lead and they match persisted state
- [ ] Loan checklist state updates persist and are auditable
- [ ] Underwriting memo generation persists and is retrievable

---

## E2E (Playwright)

- [ ] Borrower flow shows updated probability + guidance panels where designed
- [ ] Officer flow shows blockers and recommended actions on lead detail

