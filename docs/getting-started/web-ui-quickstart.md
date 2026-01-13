# Web UI Quick Start

Get started with SetuPranali's web-based admin dashboard in 2 minutes.

---

## Access the Web UI

### Option 1: Docker (Recommended)

```bash
docker run -p 8080:8080 -p 5173:5173 adeygifting/connector:latest
```

Open http://localhost:5173

### Option 2: Local Development

```bash
# Terminal 1: Start backend
cd ubi-connector
python3 -m uvicorn app.main:app --port 8080

# Terminal 2: Start frontend
cd webui
npm install
npm run dev
```

Open http://localhost:5173

---

## First Steps

### 1. Create an API Key

1. Navigate to **API Keys** (`/api-keys`)
2. Click **"Create API Key"**
3. Enter:
   - **Name**: `my-first-key`
   - **Tenant**: `default`
   - **Role**: `admin`
4. Click **"Create"**
5. **Copy the key** - it's only shown once!

### 2. Explore Datasets

1. Go to **Datasets** (`/datasets`)
2. Click on the **"orders"** dataset
3. View dimensions and metrics
4. Try a sample query

### 3. Test Query Playground

1. Navigate to **Query Playground** (`/playground`)
2. Select dataset: **"orders"**
3. Add dimension: **"city"**
4. Add metric: **"total_revenue"**
5. Click **"Execute Query"**
6. View results!

### 4. Explore Modeling Studio

1. Go to **Modeling Studio** (`/modeling`)
2. Click **"Add Source"**
3. Configure a database connection
4. Build an ERD
5. Create a semantic model

---

## Key Features

### Dashboard
- System health monitoring
- Query metrics and statistics
- Recent activity

### Query Playground
- Visual query builder
- SQL mode
- Result visualization
- Query testing

### Modeling Studio
- Schema discovery
- ERD builder
- Semantic model creation
- Query workbench

### Data Sources
- Connection management
- Connection testing
- Source configuration

### API Keys
- Key creation and management
- Usage tracking
- Key revocation

---

## Next Steps

- [Web UI Guide](../guides/web-ui.md)
- [Modeling Studio Guide](../guides/modeling-ui.md)
- [Query Playground Tutorial](first-query.md)

