# KS LOS – Enhancements Planning

## Overview
This document evaluates requested enhancements and proposes a phased plan to implement them with scientific rigour, clear acceptance criteria, and CI/CD validation. It aligns with existing project principles and documentation patterns under `doc/04_documentation`.

## Current Architecture Context
- Frontend: React (Vite) UI with panels for Chat, Credit Profile, Training, Monitoring.
- Backend: FastAPI service (`src/main.py`) with RBAC toggle, audit logging, explainability, training agents.
- Data: Postgres (pgvector), Redis cache; ML metadata in MLflow.
- Observability: OpenTelemetry Collector, Jaeger, Prometheus, Grafana (pre-provisioned dashboards).
- CI: Fairness checks, unit/e2e testing; demo mode has RBAC relaxed.

## Evaluation of Requested Enhancements
1. Login page legend removal
   - Feasibility: Trivial UI change; remove “KS LOS Demo” header until a formal design system lands.
   - Impact: None on backend; improves neutrality for demos.
2. Dual login profiles: admin and user
   - Feasibility: High. Introduce roles with scoped UI routes/tabs. Wire to backend RBAC already present.
   - Impact: Requires role-aware navigation and feature gating in frontend; minimum backend endpoint guards.
3. Task progress visualisation in Chat
   - Feasibility: Medium-High. Instrument backend workflow steps (DB lookup, classification, ML inference, enrichment) emitting progress events; render progress bar with step breakdown.
   - Impact: Prefer Server-Sent Events (SSE) or WebSocket channel for real-time progress; audit trail alignment.
4. Name/surname capture and demo suggestions
   - Feasibility: High. Add guided input form; seed demo names from real dataset slice (non-mocked) to enable autocomplete suggestions; admin toggle to enable/disable.
   - Impact: Data seeding job; frontend suggestion panel; backend search API.
5. Autocomplete grid for similar inputs
   - Feasibility: High. Client-side debounce + backend prefix search (pg_trgm or ILIKE with pgvector fallback if semantic search desired).
   - Impact: Query performance and UX; ensure accessibility and internationalisation considerations.
6. Admin configuration panel (UI controls)
   - Feasibility: High. Role-gated tab to manage demo suggestions visibility and related toggles.
   - Impact: Persist configuration in DB/Redis; respect on all relevant UI flows.
7. Admin ML model panel
   - Feasibility: Medium. Surface accuracy, drift, fairness, confusion metrics; integrate MLflow model registry and Prometheus exporter; add simple inference sandbox.
   - Impact: Requires metric exposition endpoints and Grafana integration; small UI tooling for experiments.
8. Admin metrics dashboard (charts, history)
   - Feasibility: High. Curate Grafana dashboards with sections (Latency pXX, Throughput, Errors, Drift/Fairness, Training); link-out from admin UI.
   - Impact: Provisioning updates; documentation and quick links; ensure RBAC-safe access.

## Principles Reference
This plan follows the project’s planning, validation, and documentation principles under:
- `doc/04_documentation/01_ontology-project-definition.md`
- `doc/04_documentation/02_work-breakdown-structure.md`
- `doc/04_documentation/03_version-control-setup.md`
- `doc/04_documentation/04_issue-tracking-setup.md`

## Roadmap by Phases

### Phase A: UI Hardening and Role Foundations
- Scope:
  - Remove login legend.
  - Introduce role-based login (admin/user) with gated navigation tabs.
  - Add Admin Home panel shell with links to Configuration, Model, Metrics.
- Deliverables:
  - Role-aware header and router.
  - Basic admin layout; user sees Chat + Credit Profile only.
- Architecture Touches:
  - Frontend route guards; token/role storage (secure) and logout.
  - Backend: role claims verification for sensitive endpoints.
- Acceptance Criteria:
  - Login shows no legend.
  - Admin sees Admin Home; user does not.
  - Protected endpoints return 403 to insufficient roles.
- Tests & CI:
  - Frontend: route guard unit tests (Vitest), role-based rendering tests.
  - Backend: Pytest for role checks; e2e (Playwright) for navigation.
- Risks:
  - Hidden coupling between UI routes and backend claims; mitigate via central auth utility.

### Phase B: Identity Capture and Demo Suggestions
- Scope:
  - Add name/surname capture prior to chat flow.
  - Implement demo suggestions panel (configurable), sourcing from real seeded names.
  - Autocomplete grid for similar matches.
- Deliverables:
  - Input form with debounce autocomplete.
  - Admin toggle for suggestions visibility (default enabled in demo).
- Architecture Touches:
  - Backend search endpoint for names; Postgres index strategy (btree/pg_trgm).
  - Config persistence in DB/Redis; feature flag.
- Acceptance Criteria:
  - User can select suggested demo names; randomised subset on page load.
  - Autocomplete shows relevant matches as typing proceeds.
  - Admin can enable/disable suggestion panel; change persists.
- Tests & CI:
  - Backend search correctness and performance tests.
  - Frontend autocomplete component tests and e2e path for data capture.
- Risks:
  - Data quality of demo slice; mitigate with periodic refresh and validation reports.

### Phase C: Task Progress Instrumentation (Chat)
- Scope:
  - Instrument backend workflow steps (DB lookup → feature assembly → classification → model inference → result aggregation).
  - Emit progress events via SSE/WebSocket; render progress bar with step labels and percentage.
- Deliverables:
  - Progress API channel; UI progress bar with step-by-step status (including “Looking up database”, “Classifying”, “Using ML models”, etc.).
- Architecture Touches:
  - Introduce event schema; ensure audit logs include correlation IDs.
  - Backpressure and error handling for streaming channels.
- Acceptance Criteria:
  - Progress bar reflects real steps (no simulated stages).
  - Partial failures/timeout display gracefully with recovery guidance.
- Tests & CI:
  - Backend event emission unit tests; integration tests for streaming.
  - Frontend progress UI unit/e2e tests with controlled backend.
- Risks:
  - WebSocket/SSE reliability; mitigate with heartbeat and fallback to polling.

### Phase D: Admin – Model Panel
- Scope:
  - Surface model metrics: accuracy, ROC-AUC, calibration, drift (feature and prediction), fairness (approval parity).
  - Provide simple inference sandbox (input fields → prediction and explanation).
- Deliverables:
  - UI tabs for Metrics, Drift, Fairness, Sandbox.
  - Backend endpoints exposing metrics (prom-exported or direct JSON).
- Architecture Touches:
  - MLflow integration for experiments and artefacts; Prometheus exporters for live metrics.
  - Explainability endpoint reuse (SHAP/LIME/feature attributions).
- Acceptance Criteria:
  - Metrics and drift/fairness charts render with current data.
  - Sandbox returns deterministic outputs for given inputs; explanations load.
- Tests & CI:
  - Metric computation tests; fairness gates remain under CI.
  - Frontend rendering and sandbox input/output tests.
- Risks:
  - Metric staleness; mitigate with scheduled jobs and clear timestamping.

### Phase E: Admin – Metrics Dashboard Integration
- Scope:
  - Curate Grafana dashboards grouped by sections: Latency (p50/p95/p99), Throughput, Errors, Training Jobs, Drift/Fairness, DB Health.
  - Link-out from Admin UI to specific panels.
- Deliverables:
  - Provisioned dashboard set with folder structure; admin UI shortcuts.
- Architecture Touches:
  - Grafana provisioning files updates; role-safe anonymous demo access retained.
- Acceptance Criteria:
  - All dashboards load without manual config; panel links open correctly.
- Tests & CI:
  - Provisioning validation; smoke tests for Prometheus targets and Grafana folders.
- Risks:
  - Over-provisioning complexity; mitigate with versioned dashboard JSON and docs.

### Phase F: Demo Data Seeding and Config Management
- Scope:
  - Seed realistic demo names and minimal profiles (from real but anonymised data slices, no mocks).
  - Centralise admin-configurable feature flags (e.g., showSuggestions=true by default).
- Deliverables:
  - Seed scripts and repeatable migration path; config service.
- Architecture Touches:
  - Migrations tracked; config stored with audit.
- Acceptance Criteria:
  - Demo names available; toggles persist and reflect in UI behaviour.
- Tests & CI:
  - Seed idempotency tests; config APIs tests; e2e flow for toggles.
- Risks:
  - Data provenance compliance; mitigate by documenting anonymisation and scope.

### Phase G: Documentation, Testing, and Performance
- Scope:
  - Update user/admin guides; record test plans and validation reports.
  - Add performance budgets for progress streaming and autocomplete response times.
- Deliverables:
  - Docs: `doc/acceptance.md` with budgets and reproducible steps; test reports (Playwright HTML).
- Acceptance Criteria:
  - All new features have unit, integration, and e2e coverage; performance meets budgets; acceptance script runs cleanly.
- Tests & CI:
  - Playwright journeys; Vitest components; Pytest services; CI gates for fairness and performance.
- Risks:
  - Test flakiness with streaming; mitigate via deterministic test fixtures and timeouts.

## Implementation Notes
- Security: Avoid exposing secrets; gate admin endpoints via RBAC; log sensitive events to audit securely.
- Accessibility: Autocomplete and progress components meet a11y standards (ARIA roles, keyboard navigation).
- Internationalisation: Keep labels configurable; avoid hard-coded demo-only legends.
- Hidden Coupling: Centralise auth/role utilities to prevent scatter-gun role checks.

## Acceptance Summary (Global)
- Dual roles operational with gated UI.
- Name/surname capture with demo suggestions and autocomplete.
- Progress bar shows real backend workflow stages.
- Admin panels for configuration, model metrics, and dashboards fully functional.
- All features documented and tested; CI passes fairness and performance gates.
