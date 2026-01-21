#!/bin/bash
# UBI Connector Startup Script
# Starts both backend and frontend servers

set -e

echo "=========================================="
echo "UBI Connector Startup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Running setup..."
    ./scripts/setup.sh
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if UBI_SECRET_KEY is set
if [ -z "$UBI_SECRET_KEY" ]; then
    echo "⚠️  UBI_SECRET_KEY not set. Generating..."
    export UBI_SECRET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "   Generated: $UBI_SECRET_KEY"
fi

# Set defaults
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
export ENV=${ENV:-"development"}
export CACHE_ENABLED=${CACHE_ENABLED:-"false"}

echo "Starting servers..."
echo ""

# Start backend
echo "1. Starting Backend (port 8080)..."
cd "$(dirname "$0")/.."

# Check if backend is already running
if curl -s http://localhost:8080/v1/health > /dev/null 2>&1; then
    echo "   ✅ Backend is already running on port 8080"
    echo "   Using existing backend instance"
else
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 > /tmp/ubi-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
    echo "   Logs: /tmp/ubi-backend.log"
    
    # Wait for backend to start
    sleep 3
    
    # Check if backend started
    if curl -s http://localhost:8080/v1/health > /dev/null 2>&1; then
        echo "   ✅ Backend started successfully"
    else
        echo "   ❌ Backend failed to start. Check logs: /tmp/ubi-backend.log"
        exit 1
    fi
fi

# Start frontend
echo ""
echo "2. Starting Frontend (port 5173)..."
if [ -d "webui" ]; then
    cd webui
    nohup npm run dev > /tmp/ubi-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "   Frontend PID: $FRONTEND_PID"
    echo "   Logs: /tmp/ubi-frontend.log"
    
    # Wait for frontend to start
    sleep 5
    
    # Check if frontend started
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "   ✅ Frontend is running"
    else
        echo "   ⚠️  Frontend may still be starting..."
    fi
    cd ..
else
    echo "   ⚠️  webui directory not found. Skipping frontend."
fi

echo ""
echo "=========================================="
echo "✅ Servers Started!"
echo "=========================================="
echo ""
echo "Backend:  http://localhost:8080"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8080/docs"
echo ""
echo "To stop servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID" 
echo "lsof -ti :8080 -i :5173 | xargs kill -9"
echo ""