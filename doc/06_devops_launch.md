# DevOps Launch: Local & Production

## Local Mode
- Prerequisites: Docker, Python, Node (optional for frontend), ports 8000/5000/9090/3000 free.
- Start stack:
  - `bash scripts/launch_dev.sh`
- Stop stack:
  - `bash scripts/stop_dev.sh`
- URLs:
  - API: http://localhost:8000/health
  - Metrics: http://localhost:8000/metrics
  - Observability Summary: http://localhost:8000/observability/summary
  - MLflow: http://localhost:5000/
  - Prometheus: http://localhost:9090/
  - Grafana: http://localhost:3000/
  - Drift Report: http://localhost:8000/training/drift/report

## Correlation IDs
- Send `X-Correlation-ID` header to correlate logs, spans, and MLflow runs.
- Example: `curl -H "X-Correlation-ID: test-123" http://localhost:8000/health`

## Production Mode (Guidelines)
- Run API behind a reverse proxy (Nginx) with TLS.
- Use containerized deployments for API, MLflow, Prometheus, Grafana.
- Persist volumes and set environment variables via secrets manager.
- Configure Prometheus scrape target to your API address.
- Harden Grafana (users, passwords, org).
- Enable OTLP exporter for OpenTelemetry traces to a backend (e.g., Jaeger/Tempo).

## Notes
- Logs: JSON via LOG_JSON env var.
- Metrics: Prometheus counters/histograms (requests_total, risk_inference_total, inference_latency_seconds).
- Drift: Generate via `/training/drift` and view `/training/drift/report`.
- Training: `/training/plan` then `/training/execute`.
