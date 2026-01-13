# UBI Connector Scripts

Helper scripts for setting up, starting, and testing the UBI Connector.

## Available Scripts

### 1. `setup.sh` - Initial Setup

Sets up the development environment:

```bash
./scripts/setup.sh
```

**What it does:**
- Checks Python version
- Verifies dependencies
- Generates encryption key if needed
- Checks Redis availability
- Creates database directories
- Sets up .env file

### 2. `start.sh` - Start Servers

Starts both backend and frontend servers:

```bash
./scripts/start.sh
```

**What it does:**
- Loads environment variables
- Starts backend on port 8080
- Starts frontend on port 5173
- Checks server health
- Provides server URLs and PIDs

**To stop servers:**
```bash
# Find PIDs
ps aux | grep uvicorn
ps aux | grep vite

# Kill processes
kill <PID>
```

### 3. `test_integration.py` - Integration Tests

Runs comprehensive integration tests:

```bash
python3 scripts/test_integration.py
```

**What it tests:**
- Health endpoint
- API key creation
- Dataset listing
- Query execution
- SQL execution
- Semantic models
- YAML export (feature branch)
- SQLGlot integration

**Requirements:**
- Backend server running on port 8080
- Python requests library: `pip install requests`

## Quick Start

1. **Initial Setup:**
   ```bash
   cd ubi-connector
   ./scripts/setup.sh
   ```

2. **Start Servers:**
   ```bash
   ./scripts/start.sh
   ```

3. **Run Tests:**
   ```bash
   python3 scripts/test_integration.py
   ```

## Manual Start (Alternative)

### Backend Only:
```bash
export UBI_SECRET_KEY="your-key-here"
export REDIS_URL="redis://localhost:6379/0"
python3 -m uvicorn app.main:app --port 8080
```

### Frontend Only:
```bash
cd webui
npm run dev
```

## Troubleshooting

### Server Won't Start
- Check if port 8080 is already in use: `lsof -i :8080`
- Check logs: `/tmp/ubi-backend.log` or `/tmp/ubi-frontend.log`
- Verify Python dependencies: `pip install -r requirements.txt`

### Redis Connection Failed
- Redis is optional (cache will be disabled)
- To enable: `redis-server` or `docker run -d -p 6379:6379 redis:7-alpine`

### API Key Issues
- Create API key: `curl -X POST http://localhost:8080/v1/api-keys -H "Content-Type: application/json" -d '{"name": "test", "tenant": "default", "role": "user"}'`
- Use API key in requests: `-H "X-API-Key: your-key"`

## Environment Variables

Create a `.env` file with:

```bash
UBI_SECRET_KEY=your-fernet-key-here
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
ENV=development
```

Generate encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

