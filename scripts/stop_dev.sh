#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"

echo "[KS LOS] Stopping backend and frontend dev servers..."
if [ -f "$ROOT_DIR/.pid_api" ]; then
  kill "$(cat "$ROOT_DIR/.pid_api")" || true
  rm -f "$ROOT_DIR/.pid_api"
fi
if [ -f "$ROOT_DIR/.pid_frontend" ]; then
  kill "$(cat "$ROOT_DIR/.pid_frontend")" || true
  rm -f "$ROOT_DIR/.pid_frontend"
fi

echo "[KS LOS] Stopping observability stack (Prometheus, Grafana, MLflow)..."
docker compose -f "$COMPOSE_FILE" down

echo "[KS LOS] Done."

