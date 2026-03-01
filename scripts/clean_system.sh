#!/bin/bash
set -e

# Ensure we are in the project root
cd "$(dirname "$0")/.."

echo "Cleaning up system..."

# Stop local backend
if lsof -i :8000 > /dev/null; then
    echo "Stopping local backend..."
    lsof -ti:8000 | xargs kill
    echo "Backend stopped."
else
    echo "Backend not running."
fi

# Stop local frontend
if lsof -i :5173 > /dev/null; then
    echo "Stopping local frontend..."
    lsof -ti:5173 | xargs kill
    echo "Frontend stopped."
else
    echo "Frontend not running."
fi

# Clean database
./scripts/clean_db.sh

echo "System cleaned successfully."
