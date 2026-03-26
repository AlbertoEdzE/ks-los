#!/bin/bash
# KS-LOS Development Server Launcher
# This script keeps both frontend and backend running

cd /Users/alberto/Documents/projects/ks-los

echo "═══════════════════════════════════════════════════"
echo "🚀 KS-LOS Development Stack"
echo "═══════════════════════════════════════════════════"

# Kill any existing
pkill -9 -f "vite.*5175" 2>/dev/null
pkill -9 -f "uvicorn.*8001" 2>/dev/null
sleep 2

# Start backend
echo "🔧 Starting Backend on port 8001..."
export OLLAMA_MODEL=qwen2.5:7b
python -m uvicorn src.main:app --port 8001 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Start frontend
echo "📱 Starting Frontend on port 5175..."
cd frontend
npm run dev -- --port 5175 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Wait for startup
sleep 15

# Verify
echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ STATUS"
echo "═══════════════════════════════════════════════════"

if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "🔧 Backend:  RUNNING (PID $BACKEND_PID)"
    echo "   http://localhost:8001"
else
    echo "❌ Backend:  FAILED"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "📱 Frontend: RUNNING (PID $FRONTEND_PID)"
    echo "   http://localhost:5175"
else
    echo "❌ Frontend: FAILED"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "🎯 Services are running in background"
echo "═══════════════════════════════════════════════════"
echo ""
echo "To stop: ./scripts/stop-dev.sh"
echo ""

# Keep script alive to maintain child processes
wait
