#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"

echo "[KS LOS] Bootstrapping observability stack (Prometheus, Grafana, MLflow)..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis mlflow prometheus grafana otel-collector jaeger

echo "[KS LOS] Starting FastAPI (backend) on :8000..."
# Install backend dependencies
if [ -f "$ROOT_DIR/requirements.txt" ]; then
    echo "[KS LOS] Installing backend dependencies..."
    pip install -r "$ROOT_DIR/requirements.txt" >/dev/null 2>&1 || echo "Warning: pip install failed, continuing..."
fi

export LOG_JSON=1
export OTLP_URL="http://localhost:4317"
export ENFORCE_RBAC=0

# Start Backend with nohup
(
  cd "$ROOT_DIR"
  nohup python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > "$ROOT_DIR/backend.log" 2>&1 &
  echo $! > "$ROOT_DIR/.pid_api"
)

FRONT_DIR="$ROOT_DIR/frontend"
if [ -f "$FRONT_DIR/package.json" ]; then
  echo "[KS LOS] Preparing frontend..."
  
  # Check for npm, install via brew if missing (macOS specific)
  if ! command -v npm >/dev/null 2>&1; then
    echo "[KS LOS] npm not found. Attempting to install Node.js via Homebrew..."
    if command -v brew >/dev/null 2>&1; then
        brew install node
    else
        echo "[KS LOS] Error: npm not found and Homebrew is not available. Please install Node.js manually."
        exit 1
    fi
  fi

  # Start Frontend with nohup
  (
    cd "$FRONT_DIR"
    # Install dependencies if node_modules is missing
    if [ ! -d "node_modules" ]; then
      echo "[KS LOS] Installing frontend dependencies (this may take a moment)..."
      npm install
    fi
    
    echo "[KS LOS] Starting frontend dev server..."
    # Force port 5173 to be sure
    nohup npm run dev -- --port 5173 > "$ROOT_DIR/frontend.log" 2>&1 &
    echo $! > "$ROOT_DIR/.pid_frontend"
  )

  # Wait a bit for Vite to spin up
  sleep 5
  echo "[KS LOS] Opening frontend in default browser..."
  open "http://localhost:5173"

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
