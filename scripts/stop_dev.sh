#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

graceful_kill_port() {
  local port="$1"
  local name="$2"
  local pids

  pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    return
  fi

  echo "$pids" | xargs kill 2>/dev/null || true
  sleep 1
  pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
}

echo "[KS LOS] Stopping backend and frontend dev servers..."
if [ -f "$ROOT_DIR/.pid_api" ]; then
  kill "$(cat "$ROOT_DIR/.pid_api")" || true
  rm -f "$ROOT_DIR/.pid_api"
fi
if [ -f "$ROOT_DIR/.pid_frontend" ]; then
  kill "$(cat "$ROOT_DIR/.pid_frontend")" || true
  rm -f "$ROOT_DIR/.pid_frontend"
fi

graceful_kill_port "$BACKEND_PORT" "Backend"
graceful_kill_port 5173 "Frontend (5173)"
graceful_kill_port "$FRONTEND_PORT" "Frontend"

echo "[KS LOS] Stopping observability stack (Prometheus, Grafana, MLflow)..."
if [ -f "$COMPOSE_FILE" ]; then
  docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
fi

echo "[KS LOS] Done."
