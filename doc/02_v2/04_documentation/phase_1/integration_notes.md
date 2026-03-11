# Phase 1 Integration Notes (LOS v2)

## Objective

Phase 1 establishes UI route parity with the Loan Navigator design and a contract-complete backend skeleton for the product API.

**UI Source of Truth:**  
[/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## Components Integrated

1. **Frontend (Loan Navigator UI)**
   - Routes: borrower chat, dashboard, pipeline, products, officer chat
   - Data fetching via `/api/*` endpoints

2. **Backend (Product API Skeleton)**
   - Conversations and messages endpoints
   - Phases endpoints (all/active)
   - Loans endpoints (officer only)
   - Catalog products endpoints (officer only)

3. **Persistence**
   - Schema created for conversations/messages/phases/loans/catalog products
   - Seed data for phases and catalog products (idempotent)

---

## Known Constraints (Phase 1)

- Assistant intelligence may be stubbed or rule-based; the key requirement is persistence and contract stability.
- Officer authorization may use a POC boundary (header token) as per the UI reference server.

---

## API Contract Checklist

- [ ] `/api/conversations` supports create/list/get/patch
- [ ] `/api/conversations/:id/messages` supports list and send
- [ ] `/api/phases` and `/api/phases/active` support list semantics
- [ ] `/api/loans` (officer) supports list and patch
- [ ] `/api/catalog-products` (officer) supports list/create/patch

