#!/bin/bash
# UBI Connector Setup Script
# This script helps set up the development environment

set -e

echo "=========================================="
echo "UBI Connector Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $PYTHON_VERSION"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "   ✅ Python version is compatible"
else
    echo "   ⚠️  Warning: Python 3.9+ recommended"
fi

# Check dependencies
echo ""
echo "2. Checking dependencies..."
if python3 -c "import fastapi, uvicorn, pydantic, duckdb, yaml" 2>/dev/null; then
    echo "   ✅ Core dependencies installed"
else
    echo "   ❌ Missing dependencies. Installing..."
    pip install -r requirements.txt
fi

# Generate encryption key if not set
echo ""
echo "3. Checking encryption key..."
if [ -z "$UBI_SECRET_KEY" ]; then
    echo "   ⚠️  UBI_SECRET_KEY not set. Generating..."
    export UBI_SECRET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "   ✅ Generated key: $UBI_SECRET_KEY"
    echo "   ⚠️  Add this to your .env file or export it:"
    echo "   export UBI_SECRET_KEY=\"$UBI_SECRET_KEY\""
else
    echo "   ✅ UBI_SECRET_KEY is set"
fi

# Check Redis
echo ""
echo "4. Checking Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "   ✅ Redis is running"
    else
        echo "   ⚠️  Redis is installed but not running"
        echo "   Start with: redis-server"
        echo "   Or use Docker: docker run -d -p 6379:6379 redis:7-alpine"
    fi
else
    echo "   ⚠️  Redis not installed (optional for caching)"
    echo "   Install with: brew install redis (macOS) or apt-get install redis (Linux)"
fi

# Check database files
echo ""
echo "5. Checking database files..."
if [ -d "data/db" ]; then
    echo "   ✅ Database directory exists"
else
    echo "   Creating database directory..."
    mkdir -p data/db
    echo "   ✅ Database directory created"
fi

# Create .env file if it doesn't exist
echo ""
echo "6. Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "   Creating .env file from env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "   ✅ .env file created"
        echo "   ⚠️  Please edit .env and set UBI_SECRET_KEY"
    else
        echo "   ⚠️  env.example not found"
    fi
else
    echo "   ✅ .env file exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Set UBI_SECRET_KEY in .env file"
echo "2. Start Redis (optional): redis-server"
echo "3. Start backend: python3 -m uvicorn app.main:app --port 8080"
echo "4. Start frontend: cd webui && npm run dev"
echo ""

