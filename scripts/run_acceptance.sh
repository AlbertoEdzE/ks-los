#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[Acceptance] Building frontend..."
npm -C "$ROOT/frontend" run build

echo "[Acceptance] Running backend tests..."
cd "$ROOT"
pytest -q

echo "[Acceptance] Running Playwright e2e..."
cd "$ROOT/e2e"
npx playwright test

echo "[Acceptance] Report:"
echo " - Playwright HTML: $ROOT/e2e/playwright-report/index.html"
echo " - Pytest passed; see console output above"
echo " - Frontend build succeeded"
