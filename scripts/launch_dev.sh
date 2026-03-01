#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"

echo "[KS LOS] Bootstrapping observability stack (Prometheus, Grafana, MLflow)..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis mlflow prometheus grafana

echo "[KS LOS] Starting FastAPI (backend) on :8000..."
export LOG_JSON=1
(
  cd "$ROOT_DIR"
  uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
) & echo $! > "$ROOT_DIR/.pid_api"

FRONT_DIR="$ROOT_DIR/frontend"
if [ -f "$FRONT_DIR/package.json" ]; then
  echo "[KS LOS] Starting frontend dev server..."
  (
    cd "$FRONT_DIR"
    if command -v npm >/dev/null 2>&1; then
      npm run dev
    elif command -v pnpm >/dev/null 2>&1; then
      pnpm dev
    else
      echo "No npm/pnpm found; skipping frontend dev start."
    fi
  ) & echo $! > "$ROOT_DIR/.pid_frontend"
else
  echo "[KS LOS] Frontend package.json not found; skipping frontend start."
fi

echo "[KS LOS] Stack URLs:"
echo "  API:        http://localhost:8000/health"
echo "  Metrics:    http://localhost:8000/metrics"
echo "  Observability Summary: http://localhost:8000/observability/summary"
echo "  MLflow:     http://localhost:5000/"
echo "  Prometheus: http://localhost:9090/"
echo "  Grafana:    http://localhost:3000/"
echo "  Drift Report: http://localhost:8000/training/drift/report"

