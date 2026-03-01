#!/bin/bash
set -e

# Ensure we are in the project root
cd "$(dirname "$0")/.."

echo "Starting Integration Tests..."

# Check if backend is running
if ! lsof -i :8000 > /dev/null; then
    echo "Backend not running. Starting backend..."
    source venv/bin/activate
    python -m src.main &
    BACKEND_PID=$!
    echo "Backend started with PID $BACKEND_PID"
    
    # Wait for backend to be ready
    echo "Waiting for backend to be ready..."
    sleep 10
else
    echo "Backend already running."
fi

# Run frontend tests
echo "Running Playwright E2E tests..."
cd frontend
pnpm exec playwright test

# Cleanup if we started the backend
if [ ! -z "$BACKEND_PID" ]; then
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill $BACKEND_PID
fi

echo "Integration tests completed successfully."
