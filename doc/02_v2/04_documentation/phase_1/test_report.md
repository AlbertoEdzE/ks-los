# Phase 1 Test Report (LOS v2)

## Scope

Phase 1 testing validates:

- UI route parity for the Loan Navigator pages
- Backend API endpoints exist and return expected shapes
- Officer authorization boundary is enforced for officer endpoints
- Persistence works for seeded data and basic CRUD flows

---

## Test Pyramid

### Unit Tests

- [ ] Schema validation tests for request/response payloads
- [ ] Domain rule tests (phase ordering and active phase filtering)

### Integration Tests

- [ ] Conversations: create/list/get/patch
- [ ] Messages: list/send
- [ ] Phases: list/active list
- [ ] Loans: list/patch (officer only)
- [ ] Catalog products: list/create/patch (officer only)
- [ ] Authorization: borrower requests rejected on officer resources

### E2E (Playwright) Smoke

- [ ] Borrower chat page loads and can start a conversation
- [ ] Officer dashboard loads and renders empty/seeded lead list
- [ ] Pipeline loads and renders phases
- [ ] Products page loads and renders empty/seeded product list

---

## Evidence

- Playwright report: `e2e/playwright-report/`
- Logs captured with correlation IDs for write operations

