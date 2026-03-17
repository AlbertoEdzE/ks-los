#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Starting Integration Tests..."

cleanup() {
  bash ./scripts/stop_dev.sh || true
}

trap cleanup EXIT

echo "Launching stack..."
bash ./scripts/launch_dev.sh

echo "Running Playwright E2E tests..."
npm -C e2e test

echo "Integration tests completed successfully."
