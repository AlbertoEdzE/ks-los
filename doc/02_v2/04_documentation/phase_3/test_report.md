# Phase 3 Test Report (LOS v2)

## Scope

Phase 3 testing validates:

- Officer dashboard lead list and lead detail consistency
- Officer-only authorization enforcement for protected endpoints
- Loan pipeline behavior (grouping by phase, detail patch persistence)
- Officer lifecycle chat action execution (validated and auditable)

---

## Unit Tests

- [ ] Phase ordering and activation rules are deterministic
- [ ] Action payload validators reject invalid phase/loan actions
- [ ] Status transition rules for conversations and loans are enforced

---

## Integration Tests

- [ ] `GET /api/conversations` (officer) returns lead list
- [ ] `PATCH /api/conversations/:id` (officer) persists status/assignment changes
- [ ] `GET /api/loans` (officer) returns loans
- [ ] `PATCH /api/loans/:id` (officer) persists updates and reflects on refetch
- [ ] Officer lifecycle message handling:
  - stores assistant metadata
  - applies allowed actions
  - rejects disallowed actions

### Authorization

- [ ] Borrower requests to officer endpoints return 403
- [ ] Missing/invalid officer token returns 403

---

## E2E (Playwright)

- [ ] Officer dashboard loads and can select a lead
- [ ] Pipeline loads, shows phases, and shows loans in correct columns
- [ ] Loan detail can be opened and patched; refresh preserves changes

