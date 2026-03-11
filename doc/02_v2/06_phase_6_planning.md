# Phase 6 Plan: Reliability, CI/CD, Security (LOS v2)

## Objectives

1. CI/CD pipeline for frontend, backend, and end-to-end tests.
2. Automated quality gates: lint, typecheck, unit tests, integration tests, Playwright.
3. Secrets management and environment configuration for v2.
4. Performance/load baseline and regression checks aligned to acceptance budgets.
5. Observability plumbing: correlation IDs, audit events, and metrics coverage.

## Scope

- CI workflows for:
  - frontend build and tests
  - backend build and tests
  - Playwright E2E smoke on PR and full regression on main
- Security hygiene:
  - secret scanning
  - dependency audits
  - basic static analysis
- Performance baseline:
  - automated checks for critical endpoints (conversations list, loans list, message send)
- Observability:
  - standard request logging with correlation IDs
  - audit trail requirements for every write path

## Deliverables

1. CI workflows for PR and main merges, including artifacts upload (Playwright reports).
2. Documented environment variables for all runtime services (frontend + backend).
3. Performance scripts and baseline reports for each release checkpoint.
4. Security checks in CI (secret scanning, dependency audit) with failure gates.
5. Observability initialization checklist and minimum dashboard metrics list.

## Success Criteria

1. Green CI is required for merges; no bypass for protected branches.
2. Secrets are not committed; environment is configured securely in CI.
3. Performance baselines are tracked per release and regressions block merges.
4. Playwright reports are generated deterministically with seeded data.

