# Quick Start

Get SetuPranali running and querying data in **5 minutes**.

---

## Step 1: Start the Connector

=== "Docker (Recommended)"

    ```bash
    # Pull and run the latest image
    docker run -d \
      --name ubi-connector \
      -p 8080:8080 \
      -e UBI_SECRET_KEY=$(openssl rand -base64 32) \
      setupranali/connector:latest
    ```

=== "Docker Compose"

    ```yaml
    # docker-compose.yml
    version: '3.8'
    services:
      connector:
        image: setupranali/connector:latest
        ports:
          - "8080:8080"
        environment:
          - UBI_SECRET_KEY=${UBI_SECRET_KEY}
          - REDIS_URL=redis://redis:6379
        depends_on:
          - redis
      
      redis:
        image: redis:7-alpine
    ```

    ```bash
    docker compose up -d
    ```

=== "From Source"

    ```bash
    git clone https://github.com/setupranali/setupranali.github.io.git
    cd setupranali
    
    # Create virtual environment
    python -m venv .venv
    source .venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Start the server
    python -m uvicorn app.main:app --port 8080
    ```

Verify it's running:

```bash
curl http://localhost:8080/health
```

Expected response:

```json
{"status": "ok", "version": "1.0.0"}
```

---

## Step 2: Register a Data Source

Add your database connection. The credentials are encrypted at rest.

=== "Snowflake"

    ```bash
    curl -X POST http://localhost:8080/v1/sources \
      -H "X-API-Key: admin-key" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "snowflake-prod",
        "type": "snowflake",
        "connection": {
          "account": "abc123.us-east-1",
          "user": "BI_SERVICE",
          "password": "your-password",
          "warehouse": "ANALYTICS_WH",
          "database": "ANALYTICS",
          "schema": "PUBLIC"
        }
      }'
    ```

=== "PostgreSQL"

    ```bash
    curl -X POST http://localhost:8080/v1/sources \
      -H "X-API-Key: admin-key" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "postgres-prod",
        "type": "postgres",
        "connection": {
          "host": "db.example.com",
          "port": 5432,
          "database": "analytics",
          "user": "readonly",
          "password": "your-password"
        }
      }'
    ```

=== "BigQuery"

    ```bash
    curl -X POST http://localhost:8080/v1/sources \
      -H "X-API-Key: admin-key" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "bigquery-prod",
        "type": "bigquery",
        "connection": {
          "project_id": "my-project",
          "credentials_json": "{...service-account-key...}"
        }
      }'
    ```

!!! success "Source Registered"
    Your database credentials are now encrypted and stored securely.
    You'll reference this source by name in your datasets.

---

## Step 3: Define a Dataset

Create a `catalog.yaml` file with your semantic model:

```yaml
datasets:
  - name: sales
    source: snowflake-prod  # References the source you just created
    table: fact_sales
    
    dimensions:
      - name: region
        type: string
        expr: region_name
        description: Sales region
      
      - name: product
        type: string
        expr: product_category
        description: Product category
      
      - name: order_date
        type: date
        expr: order_date
        description: Order date
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(sale_amount)"
        description: Total revenue
      
      - name: orders
        type: number
        expr: "COUNT(*)"
        description: Number of orders
      
      - name: avg_order_value
        type: number
        expr: "AVG(sale_amount)"
        description: Average order value
    
    # Optional: Row-level security
    rls:
      tenant_column: tenant_id
```

The connector automatically loads `catalog.yaml` on startup.

---

## Step 4: Create an API Key

API keys control access and enable row-level security:

```yaml
# Add to your config or env
api_keys:
  # Admin key for management
  - key: "admin-key"
    role: admin
  
  # Tenant-specific key with RLS
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
  
  # Another tenant
  - key: "pk_globex_xyz789"
    tenant: globex_inc
    role: analyst
```

!!! info "Row-Level Security"
    When a user queries with `pk_acme_abc123`, they only see rows where 
    `tenant_id = 'acme_corp'`. This is automatic—no extra code needed.

---

## Step 5: Query Your Data

### Option A: REST API

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region", "product"],
    "metrics": ["revenue", "orders"],
    "filters": [
      {"field": "order_date", "op": ">=", "value": "2024-01-01"}
    ]
  }'
```

Response:

```json
{
  "columns": [
    {"name": "region", "type": "string"},
    {"name": "product", "type": "string"},
    {"name": "revenue", "type": "number"},
    {"name": "orders", "type": "number"}
  ],
  "rows": [
    ["North", "Electronics", 125000.00, 342],
    ["South", "Furniture", 89000.00, 156],
    ["East", "Electronics", 156000.00, 421]
  ],
  "stats": {
    "rowCount": 3,
    "executionTimeMs": 234
  }
}
```

### Option B: Connect Power BI

1. In Power BI Desktop, go to **Get Data** → **OData Feed**
2. Enter URL: `http://localhost:8080/odata/sales`
3. Select **Advanced** → Add custom header:
   - `X-API-Key`: `pk_acme_abc123`
4. Click **OK** and load your data

### Option C: Connect Tableau

1. Open Tableau Desktop
2. Go to **Connect** → **Web Data Connector**
3. Enter URL: `http://localhost:8080/wdc/`
4. Enter your API key when prompted
5. Select dataset and load

---

## 🎉 You're Done!

You now have:

- [x] A running SetuPranali
- [x] Encrypted database connection
- [x] Semantic dataset with metrics
- [x] Secure API access with RLS
- [x] BI tool connected

---

## Next Steps

<div class="grid cards" markdown>

-   **Add More Datasets**

    ---

    Define additional datasets in your catalog.

    [:octicons-arrow-right-24: Dataset Guide](../guides/datasets.md)

-   **Configure RLS**

    ---

    Set up row-level security for multi-tenant access.

    [:octicons-arrow-right-24: RLS Guide](../guides/rls.md)

-   **Enable Caching**

    ---

    Improve performance with Redis caching.

    [:octicons-arrow-right-24: Caching](../concepts/caching.md)

-   **Deploy to Production**

    ---

    Deploy with Docker or Kubernetes.

    [:octicons-arrow-right-24: Deployment](../deployment/index.md)

</div>

