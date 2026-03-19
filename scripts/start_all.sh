#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export ROOT_DIR

cleanup() {
  echo "Stopping services..."
  bash "$ROOT_DIR/scripts/stop_dev.sh" || true
  exit
}
trap cleanup SIGINT SIGTERM

echo "Starting Infrastructure..."
cd "$ROOT_DIR"

echo "Launching dev stack..."
bash "$ROOT_DIR/scripts/launch_dev.sh"

PYTHON_BIN=""
if [ -x "$ROOT_DIR/venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
fi

if [ -n "$PYTHON_BIN" ] && [ -f "$ROOT_DIR/scripts/init_kb.py" ]; then
  "$PYTHON_BIN" "$ROOT_DIR/scripts/init_kb.py" || true
fi
echo "System running. Press Ctrl+C to stop."
while true; do
  sleep 2
done
