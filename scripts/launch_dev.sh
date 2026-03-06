#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"

# Function to check and free a port
check_and_free_port() {
    local port=$1
    local service_name=$2
    
    if lsof -i :$port >/dev/null 2>&1; then
        echo "[KS LOS] Port $port ($service_name) is in use. Attempting to free..."
        local pids=$(lsof -ti :$port || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            echo "[KS LOS] Freed port $port."
        fi
    fi
}

# Function to ensure Docker is running
ensure_docker_running() {
    if ! docker info > /dev/null 2>&1; then
        echo "[KS LOS] Docker is not running."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "[KS LOS] Attempting to start Docker Desktop..."
            open -a Docker
            echo "[KS LOS] Waiting for Docker to start (this may take a minute)..."
            local retries=0
            while ! docker info > /dev/null 2>&1; do
                sleep 2
                printf "."
                retries=$((retries+1))
                if [ $retries -gt 60 ]; then
                    echo ""
                    echo "[KS LOS] Error: Timed out waiting for Docker to start."
                    exit 1
                fi
            done
            echo ""
            echo "[KS LOS] Docker started successfully."
        else
            echo "[KS LOS] Error: Docker is not running. Please start it manually."
            exit 1
        fi
    fi
}

ensure_docker_running

echo "[KS LOS] Cleaning up previous session..."

# 1. Stop Docker services
if [ -f "$COMPOSE_FILE" ]; then
    echo "[KS LOS] Stopping Docker containers..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
fi

# 2. Kill local processes on critical ports
# Docker services ports (in case local services are running or docker failed to clean up)
check_and_free_port 6379 "Redis"
check_and_free_port 5432 "Postgres"
check_and_free_port 5000 "MLflow"
check_and_free_port 9090 "Prometheus"
check_and_free_port 3000 "Grafana"
check_and_free_port 4317 "Otel Collector"
check_and_free_port 16686 "Jaeger"

# App ports
check_and_free_port 8000 "Backend API"
check_and_free_port 5173 "Frontend"

echo "[KS LOS] Bootstrapping observability stack (Prometheus, Grafana, MLflow)..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis mlflow prometheus grafana otel-collector jaeger

echo "[KS LOS] Starting FastAPI (backend) on :8000..."
# Install backend dependencies
if [ -f "$ROOT_DIR/requirements.txt" ]; then
    echo "[KS LOS] Installing backend dependencies..."
    pip install -r "$ROOT_DIR/requirements.txt" || echo "Warning: pip install failed, continuing..."
fi

export LOG_JSON=1
export OTLP_URL="http://localhost:4317"
export ENFORCE_RBAC=0
export MLFLOW_TRACKING_URI="http://localhost:5000"

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
    
    nohup npm run dev -- --port 5173 --strictPort > "$ROOT_DIR/frontend.log" 2>&1 &
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
