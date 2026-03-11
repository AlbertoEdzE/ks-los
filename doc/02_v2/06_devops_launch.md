# DevOps + Launch Checklist (LOS v2)

## Objective

Define the operational checklist to run LOS v2 reliably in local development and staged demos, with repeatable test evidence and validation artifacts.

---

## 1. Environment Readiness

- [ ] Backend environment variables defined (database, auth, LLM provider)
- [ ] Frontend configured to call the v2 product API base URL
- [ ] Seed routine exists and is idempotent (phases/products)

---

## 2. CI Quality Gates (Minimum)

- [ ] Lint
- [ ] Typecheck
- [ ] Unit tests
- [ ] Integration tests
- [ ] Playwright E2E (smoke on PR, full on main)

---

## 3. Observability Readiness

- [ ] Correlation ID support on all requests
- [ ] Audit events for all write paths and automated actions
- [ ] Metrics for key workflows (lead creation, qualification, loan stage time)

---

## 4. Release Readiness

- [ ] Acceptance guide steps can be executed end-to-end
- [ ] Phase validation reports updated and committed
- [ ] Playwright report generated and stored
- [ ] Release tag applied only after passing gates

