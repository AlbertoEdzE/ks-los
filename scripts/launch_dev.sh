#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker-compose.yml"
SKIP_DOCKER="${SKIP_DOCKER:-0}"
INSTALL_BACKEND_DEPS="${INSTALL_BACKEND_DEPS:-1}"
INSTALL_FRONTEND_DEPS="${INSTALL_FRONTEND_DEPS:-1}"

if command -v git >/dev/null 2>&1 && [ -d "$ROOT_DIR/.git" ]; then
  echo "[KS LOS] Repo: $ROOT_DIR (git $(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo 'unknown'))"
else
  echo "[KS LOS] Repo: $ROOT_DIR"
fi

trim_ws() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

load_dotenv() {
  local dotenv_file="$1"
  [ -f "$dotenv_file" ] || return 0

  while IFS= read -r raw || [ -n "$raw" ]; do
    local line
    line="$(trim_ws "$raw")"

    if [ -z "$line" ]; then
      continue
    fi
    case "$line" in
      \#*) continue ;;
    esac

    if [[ "$line" == export\ * ]]; then
      line="${line#export }"
      line="$(trim_ws "$line")"
    fi

    local key value
    if [[ "$line" == *"="* ]]; then
      key="$(trim_ws "${line%%=*}")"
      value="$(trim_ws "${line#*=}")"
    elif [[ "$line" == *":"* ]]; then
      key="$(trim_ws "${line%%:*}")"
      value="$(trim_ws "${line#*:}")"
    else
      continue
    fi

    if [ -z "$key" ]; then
      continue
    fi

    if [[ "$key" == "key" || "$key" == "openai_key" || "$key" == "openai.api_key" ]]; then
      if [ -z "${OPENAI_API_KEY:-}" ]; then
        key="OPENAI_API_KEY"
      else
        continue
      fi
    fi

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value#\"}"
      value="${value%\"}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value#\'}"
      value="${value%\'}"
    fi

    export "$key=$value"
  done < "$dotenv_file"
}

load_dotenv "$ROOT_DIR/.env"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
MLFLOW_PORT="${MLFLOW_PORT:-5000}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"

wait_for_http() {
    local url="$1"
    local name="$2"
    local timeout_s="${3:-30}"
    local start_ts
    start_ts="$(date +%s)"

    while true; do
        if curl -fsS "$url" >/dev/null 2>&1; then
            echo "[KS LOS] $name is ready: $url"
            return 0
        fi

        local now_ts
        now_ts="$(date +%s)"
        if [ $((now_ts - start_ts)) -ge "$timeout_s" ]; then
            echo "[KS LOS] Error: $name did not become ready within ${timeout_s}s: $url"
            return 1
        fi
        sleep 1
    done
}

tail_log() {
    local file="$1"
    local name="$2"
    if [ -f "$file" ]; then
        echo "[KS LOS] Last 80 lines of $name log ($file):"
        tail -n 80 "$file" || true
    else
        echo "[KS LOS] $name log not found: $file"
    fi
}

check_and_free_port() {
    local port=$1
    local service_name=$2
    
    if lsof -i :$port >/dev/null 2>&1; then
        if lsof -nP -i :$port | grep -qi 'com.docke'; then
            echo "[KS LOS] Port $port ($service_name) is used by Docker Desktop. Skipping process kill."
            return 0
        fi
        echo "[KS LOS] Port $port ($service_name) is in use. Attempting to free..."
        local pids
        pids="$(lsof -ti :"$port" 2>/dev/null || true)"
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill 2>/dev/null || true
            sleep 1
            pids="$(lsof -ti :"$port" 2>/dev/null || true)"
            if [ -n "$pids" ]; then
              echo "$pids" | xargs kill -9 2>/dev/null || true
            fi
            echo "[KS LOS] Freed port $port ($service_name)."
        fi
    fi
}

free_docker_port() {
  local port="$1"
  local name="$2"
  if command -v docker >/dev/null 2>&1; then
    local ids
    ids="$(docker ps --format '{{.ID}} {{.Ports}}' | awk '/0.0.0.0:'"$port"'->/ {print $1}')"
    if [ -n "$ids" ]; then
      echo "[KS LOS] Stopping Docker containers using port $port ($name)..."
      for id in $ids; do
        docker stop "$id" >/dev/null 2>&1 || true
      done
    fi
  fi
}

# Function to ensure Docker is running
ensure_docker_running() {
    if [ "$SKIP_DOCKER" = "1" ]; then
        return 0
    fi
    if ! command -v docker >/dev/null 2>&1; then
        echo "[KS LOS] Warning: docker not found. Skipping observability stack."
        SKIP_DOCKER=1
        return 0
    fi
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
                    echo "[KS LOS] Warning: Timed out waiting for Docker to start. Continuing without Docker services."
                    SKIP_DOCKER=1
                    return 0
                fi
            done
            echo ""
            echo "[KS LOS] Docker started successfully."
        else
            echo "[KS LOS] Warning: Docker is not running. Continuing without Docker services."
            SKIP_DOCKER=1
            return 0
        fi
    fi
}

ensure_docker_running

echo "[KS LOS] Cleaning up previous session..."

# 1. Stop Docker services
if [ "$SKIP_DOCKER" != "1" ] && [ -f "$COMPOSE_FILE" ]; then
    echo "[KS LOS] Stopping Docker containers..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
    echo "[KS LOS] Pulling latest Docker images..."
    docker compose -f "$COMPOSE_FILE" pull || true
fi

# 2. Kill local processes on critical ports
# Docker services ports (in case local services are running or docker failed to clean up)
check_and_free_port 6379 "Redis"
check_and_free_port 5432 "Postgres"
check_and_free_port "$MLFLOW_PORT" "MLflow"
check_and_free_port 9090 "Prometheus"
check_and_free_port 3000 "LangFuse"
check_and_free_port 3001 "Grafana"
check_and_free_port 4317 "Otel Collector"
check_and_free_port 16686 "Jaeger"

# App ports
if [ "$SKIP_DOCKER" != "1" ]; then
  free_docker_port "$BACKEND_PORT" "Backend API"
fi
check_and_free_port "$BACKEND_PORT" "Backend API"
check_and_free_port 5173 "Frontend"
check_and_free_port "$FRONTEND_PORT" "Frontend"

export MLFLOW_PORT
export BACKEND_PORT

ensure_docker_running

if [ "$SKIP_DOCKER" != "1" ]; then
  echo "[KS LOS] Bootstrapping observability stack (Prometheus, Grafana, MLflow)..."
  docker compose -f "$COMPOSE_FILE" up -d postgres redis postgres_exporter mlflow prometheus grafana otel-collector jaeger langfuse
else
  echo "[KS LOS] Skipping observability stack (Docker disabled)."
fi

if [ "$SKIP_DOCKER" != "1" ]; then
  POSTGRES_USER="${POSTGRES_USER:-ks_los}"
  POSTGRES_DB="${POSTGRES_DB:-ks_los_db}"
  LANGFUSE_DB="${LANGFUSE_DB:-langfuse_db}"
  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' | grep -qx 'ks_los_postgres'; then
      echo "[KS LOS] Ensuring Postgres database '${LANGFUSE_DB}' exists for LangFuse..."
      if ! docker exec ks_los_postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "select 1 from pg_database where datname='${LANGFUSE_DB}'" | grep -q 1; then
        docker exec ks_los_postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "create database ${LANGFUSE_DB}" >/dev/null 2>&1 || true
      fi
    fi
  fi
fi

# Ensure Ollama is installed and serving a model locally (optional but recommended for LLM features)
ensure_ollama_running() {
  if command -v ollama >/dev/null 2>&1; then
    if ! curl -fsS "http://localhost:${OLLAMA_PORT}/api/version" >/dev/null 2>&1; then
      echo "[KS LOS] Starting Ollama daemon..."
      nohup ollama serve > "$ROOT_DIR/ollama.log" 2>&1 &
      for i in $(seq 1 30); do
        if curl -fsS "http://localhost:${OLLAMA_PORT}/api/version" >/dev/null 2>&1; then
          break
        fi
        sleep 1
      done
    fi
    if curl -fsS "http://localhost:${OLLAMA_PORT}/api/version" >/dev/null 2>&1; then
      echo "[KS LOS] Ensuring model '${OLLAMA_MODEL}' is available..."
      ollama pull "${OLLAMA_MODEL}" >/dev/null 2>&1 || true
    else
      echo "[KS LOS] Warning: Ollama daemon did not respond on :${OLLAMA_PORT}. LLM calls may be disabled."
    fi
  else
    echo "[KS LOS] Warning: 'ollama' not found; local LLM will be unavailable."
    if command -v brew >/dev/null 2>&1; then
      echo "[KS LOS] You can install it via: brew install ollama"
    fi
  fi
}
ensure_ollama_running

open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || echo "[KS LOS] Please open: $url"
  else
    echo "[KS LOS] Please open in your browser: $url"
  fi
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "$ROOT_DIR/venv/bin/python" ]; then
    # Guard against a copied/broken venv (e.g. symlinks to a different machine).
    if "$ROOT_DIR/venv/bin/python" -c "import sys; print(sys.executable)" >/dev/null 2>&1; then
      PYTHON_BIN="$ROOT_DIR/venv/bin/python"
    else
      echo "[KS LOS] Warning: existing venv looks broken. Removing $ROOT_DIR/venv ..."
      rm -rf "$ROOT_DIR/venv" || true
    fi
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "[KS LOS] Error: Python not found."
    exit 1
  fi
fi

VSTR="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo '')"
REQ_OK=0
case "$VSTR" in
  3.11|3.12|3.13) REQ_OK=1 ;;
esac
if [ "$REQ_OK" -ne 1 ]; then
  echo "[KS LOS] Warning: Python $VSTR detected; 3.11–3.13 recommended."
fi

if [ ! -x "$ROOT_DIR/venv/bin/python" ]; then
  echo "[KS LOS] Creating python venv at $ROOT_DIR/venv ..."
  if ! "$PYTHON_BIN" -m venv "$ROOT_DIR/venv"; then
    echo "[KS LOS] Warning: failed to create venv. Continuing with system python: $PYTHON_BIN"
  fi
fi
if [ -x "$ROOT_DIR/venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
fi

# Optional pip flags (avoid breaking on macOS; needed on some Linux system pythons)
declare -a PIP_FLAGS
PIP_FLAGS=()
if [[ "$(uname -s)" == "Linux" ]] && [[ "$PYTHON_BIN" != "$ROOT_DIR/venv/bin/python" ]]; then
  PIP_FLAGS+=(--break-system-packages)
fi

"$PYTHON_BIN" -m pip install -U pip "wheel<0.46" setuptools ${PIP_FLAGS[@]+"${PIP_FLAGS[@]}"} >/dev/null 2>&1 || true
if [ "$INSTALL_BACKEND_DEPS" = "1" ] && [ -f "$ROOT_DIR/requirements.txt" ]; then
  echo "[KS LOS] Installing backend dependencies..."
  "$PYTHON_BIN" -m pip install ${PIP_FLAGS[@]+"${PIP_FLAGS[@]}"} -r "$ROOT_DIR/requirements.txt"
elif [ "$INSTALL_BACKEND_DEPS" != "1" ]; then
  echo "[KS LOS] Installing minimal backend dependencies (INSTALL_BACKEND_DEPS=0)..."
  "$PYTHON_BIN" -m pip install ${PIP_FLAGS[@]+"${PIP_FLAGS[@]}"} fastapi "uvicorn[standard]" >/dev/null 2>&1 || true
fi

if ! "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
  echo "[KS LOS] Error: uvicorn not installed for $PYTHON_BIN."
  exit 1
fi

if ! command -v tesseract >/dev/null 2>&1; then
  echo "[KS LOS] Warning: tesseract not found; image OCR endpoints will return 501."
fi
if ! command -v pdftotext >/dev/null 2>&1; then
  echo "[KS LOS] Warning: pdftotext not found; PDF OCR endpoints will return 501."
fi

echo "[KS LOS] Starting FastAPI (backend) on :$BACKEND_PORT..."

export LOG_JSON=1
export OTLP_URL="http://localhost:4317"
export ENFORCE_RBAC=0
export MLFLOW_TRACKING_URI="http://localhost:$MLFLOW_PORT"
export OLLAMA_MODEL="${OLLAMA_MODEL}"

# Start Backend with nohup
(
  cd "$ROOT_DIR"
  nohup "$PYTHON_BIN" -m uvicorn src.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload --reload-dir "src" --reload-exclude "frontend/node_modules/*" > "$ROOT_DIR/backend.log" 2>&1 &
  echo $! > "$ROOT_DIR/.pid_api"
)

if ! wait_for_http "http://localhost:$BACKEND_PORT/health" "Backend API" 45; then
  tail_log "$ROOT_DIR/backend.log" "backend"
  echo "[KS LOS] Tip: if you see import errors, activate venv and reinstall deps."
  exit 1
fi

# Initialize knowledge base or any seed data if script is present
if [ -f "$ROOT_DIR/scripts/init_kb.py" ]; then
  echo "[KS LOS] Initializing knowledge base..."
  "$PYTHON_BIN" "$ROOT_DIR/scripts/init_kb.py" || true
fi

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
    if [ "$INSTALL_FRONTEND_DEPS" = "1" ]; then
      echo "[KS LOS] Installing frontend dependencies (this may take a moment)..."
      if [ -f "package-lock.json" ]; then
        npm ci || npm install
      else
        npm install
      fi
    else
      echo "[KS LOS] Skipping frontend dependency install (INSTALL_FRONTEND_DEPS=0)."
    fi
    
    echo "[KS LOS] Starting frontend dev server..."
    
    VITE_API_URL="http://localhost:$BACKEND_PORT" nohup npm run dev -- --port "$FRONTEND_PORT" --strictPort > "$ROOT_DIR/frontend.log" 2>&1 &
    echo $! > "$ROOT_DIR/.pid_frontend"
  )

  if ! wait_for_http "http://localhost:$FRONTEND_PORT" "Frontend" 60; then
    tail_log "$ROOT_DIR/frontend.log" "frontend"
    exit 1
  fi
  echo "[KS LOS] Opening frontend in default browser..."
  open_url "http://localhost:$FRONTEND_PORT"

else
  echo "[KS LOS] Frontend package.json not found; skipping frontend start."
fi

echo "[KS LOS] Stack URLs:"
echo "  API:        http://localhost:$BACKEND_PORT/health"
echo "  Metrics:    http://localhost:$BACKEND_PORT/metrics"
echo "  Observability Summary (Authorization: Bearer ${DEV_OFFICER_TOKEN:-loan-officer-access}): http://localhost:$BACKEND_PORT/observability/summary"
echo "  MLflow:     http://localhost:$MLFLOW_PORT/"
echo "  Prometheus: http://localhost:9090/"
echo "  LangFuse:   http://localhost:3000/"
echo "  Grafana:    http://localhost:3001/"
echo "  Drift Report (Authorization: Bearer ${DEV_OFFICER_TOKEN:-loan-officer-access}): http://localhost:$BACKEND_PORT/training/drift/report"
