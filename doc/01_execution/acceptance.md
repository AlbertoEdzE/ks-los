# KS LOS – Acceptance Guide

## Scope
- Verify admin/user login flows, synthetic data controls, identity capture with suggestions, chat progress instrumentation, model explainability, and Grafana dashboards.

## Performance Budgets
- Autocomplete prefix query p95 ≤ 150 ms (demo dataset).
- SSE progress cadence ~500 ms; UI update p95 ≤ 50 ms.
- Backend progress endpoints p95 ≤ 300 ms under demo load.

## End-to-End Steps
1. Launch stack:
   - `bash scripts/launch_dev.sh`
2. Admin login and synthetic control:
   - Navigate to Admin tab → Synthetic Data
   - Start generation with desired parameters; observe SSE progress
   - Validate output via the Validate button
3. User login and chat:
   - Enter name and surname; observe suggestions
   - Send a chat message; observe progress bar and SSE updates
4. Model panel:
   - Open Admin → Model; view Observability Summary
   - Run Sandbox: generate profile and explain inference; confirm score and features
5. Metrics:
   - Open Admin → Metrics; follow links to Grafana and Prometheus metrics; confirm panels load
6. Seeding:
   - `POST /admin/seed/demo-names?reset=true&count=500` yields totals; repeat without reset to confirm idempotence

## Scripts
- `scripts/run_acceptance.sh` runs backend tests, frontend build, and root e2e suite; captures Playwright report.

## Audit and Correlation IDs
- Ensure X-Correlation-ID propagates or is generated; audit logs include event, endpoint, status, meta.

## Artefacts
- Playwright HTML report saved under `e2e/playwright-report`.
- Dashboard JSON under `infrastructure/observability/grafana/dashboards/json`.

