#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

echo "Cleaning database..."
docker-compose -f infrastructure/docker-compose.yml down -v
echo "Database cleaned."
