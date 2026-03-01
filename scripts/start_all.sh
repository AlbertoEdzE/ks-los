#!/bin/bash
set -e

# Function to clean up background processes on exit
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p) 2>/dev/null
    make down
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Infrastructure..."
make up

echo "Waiting for services to be healthy..."
sleep 10
make check-infra

echo "Initializing Knowledge Base..."
source venv/bin/activate
python scripts/init_kb.py

echo "Starting Backend..."
python -m src.main &
BACKEND_PID=$!

echo "Starting Frontend..."
cd frontend
pnpm dev &
FRONTEND_PID=$!

echo "System running. Press Ctrl+C to stop."
wait $BACKEND_PID $FRONTEND_PID
