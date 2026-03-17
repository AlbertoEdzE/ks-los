#!/bin/bash
set -euo pipefail

# Ensure we are in the project root
cd "$(dirname "$0")/.."

echo "Cleaning up system..."

graceful_kill_port() {
  local port="$1"
  local name="$2"

  local pids
  pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    echo "$name not running."
    return
  fi

  echo "Stopping $name..."
  echo "$pids" | xargs kill 2>/dev/null || true
  sleep 1

  pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
  echo "$name stopped."
}

if [ -f "./scripts/stop_dev.sh" ]; then
  bash ./scripts/stop_dev.sh || true
fi

graceful_kill_port 8000 "Backend"
graceful_kill_port 5173 "Frontend (5173)"
graceful_kill_port 5174 "Frontend (5174)"

# Clean database
./scripts/clean_db.sh

rm -f .pid_api .pid_frontend backend.log frontend.log ks_los_v2.db

echo "System cleaned successfully."
