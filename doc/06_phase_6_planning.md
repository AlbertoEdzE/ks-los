# Phase 6 Plan: Reliability, CI/CD, Security

## Objectives
1. CI/CD pipeline for backend, frontend, and infra.
2. Automated tests in pipeline with coverage gates.
3. Secrets management and environment configuration.
4. Performance/load baseline and regression checks.

## Scope
- GitHub Actions workflows: lint, test, build, publish Docker images.
- Infra: production compose or Helm charts (future).
- Security: dependency scanning, basic SAST, secret scanning.
- Performance: k6 scripts to exercise key endpoints.

## Deliverables
1. Workflows: backend, frontend, infra.
2. Docker images published to registry (tagged).
3. k6 performance scripts and reports.
4. Documentation for deployment steps and environment variables.
5. OTLP exporter initialization with local Jaeger via collector.
6. Enhanced Grafana panels for endpoint error rates and request throughput.

## Success Criteria
1. Green CI for PRs and main merges.
2. No secrets in repo; env configured via CI/CD securely.
3. Performance baseline achieved and tracked per release.
