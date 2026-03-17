#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="infrastructure/docker-compose.yml"

echo "Cleaning database..."
if ! docker info >/dev/null 2>&1; then
  if [[ "${OSTYPE:-}" == "darwin"* ]]; then
    open -a Docker || true
    retries=0
    while ! docker info >/dev/null 2>&1; do
      sleep 2
      retries=$((retries+1))
      if [ "$retries" -gt 60 ]; then
        echo "Docker is not running."
        exit 1
      fi
    done
  else
    echo "Docker is not running."
    exit 1
  fi
fi
if [ -f "$COMPOSE_FILE" ]; then
  docker compose -f "$COMPOSE_FILE" down -v --remove-orphans
else
  echo "Compose file not found at $COMPOSE_FILE"
  exit 1
fi
echo "Database cleaned."
