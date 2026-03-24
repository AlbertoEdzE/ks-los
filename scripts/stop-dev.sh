#!/bin/bash
# Stop KS-LOS Development Servers

pkill -9 -f "vite.*5175" 2>/dev/null
pkill -9 -f "uvicorn.*8001" 2>/dev/null

echo "✅ All servers stopped"
