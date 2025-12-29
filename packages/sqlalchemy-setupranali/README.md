# sqlalchemy-setupranali

SQLAlchemy dialect for SetuPranali semantic layer - Apache Superset compatible.

## Features

- 🔌 **Native SQLAlchemy Dialect** - Works with all SQLAlchemy-based tools
- 🦸 **Apache Superset Ready** - First-class Superset integration
- 🔐 **API Key Authentication** - Secure connection to SetuPranali
- 📊 **Schema Introspection** - Auto-discover datasets, dimensions, and metrics
- 🚀 **Connection Pooling** - Efficient HTTP connection reuse

## Installation

```bash
pip install sqlalchemy-setupranali
```

Or install from source:

```bash
git clone https://github.com/setupranali/setupranali.github.io.git
cd packages/sqlalchemy-setupranali
pip install -e .
```

## Quick Start

### SQLAlchemy

```python
from sqlalchemy import create_engine, text

# Create engine
engine = create_engine(
    "setupranali+http://localhost:8080?api_key=your-api-key"
)

# Execute query
with engine.connect() as conn:
    result = conn.execute(text("SELECT region, SUM(amount) as revenue FROM orders GROUP BY region"))
    for row in result:
        print(row)
```

### Apache Superset

1. Go to **Data** > **Databases** > **+ Database**
2. Select **Other** as database type
3. Enter SQLAlchemy URI:
   ```
   setupranali+http://your-server:8080?api_key=your-api-key
   ```
4. Click **Test Connection** then **Connect**

## Connection URI Format

```
setupranali+http://host:port?api_key=key&database=dataset&timeout=30
setupranali+https://host:port?api_key=key&database=dataset
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `host` | SetuPranali server hostname | `localhost` |
| `port` | Server port | `8080` |
| `api_key` | API key for authentication | (required) |
| `database` | Default dataset for RLS context | (none) |
| `timeout` | Request timeout in seconds | `30` |

### Examples

```python
# Local development
engine = create_engine("setupranali+http://localhost:8080?api_key=my-key")

# Production with HTTPS
engine = create_engine("setupranali+https://bi-api.company.com?api_key=prod-key")

# With default dataset
engine = create_engine("setupranali+http://localhost:8080?api_key=my-key&database=orders")

# With custom timeout
engine = create_engine("setupranali+http://localhost:8080?api_key=my-key&timeout=60")
```

## Usage Examples

### Basic Query

```python
from sqlalchemy import create_engine, text

engine = create_engine("setupranali+http://localhost:8080?api_key=my-key")

with engine.connect() as conn:
    # Simple aggregation
    result = conn.execute(text("""
        SELECT 
            region,
            SUM(amount) as revenue,
            COUNT(*) as order_count
        FROM orders
        GROUP BY region
        ORDER BY revenue DESC
    """))
    
    for row in result:
        print(f"{row.region}: ${row.revenue:,.2f}")
```

### With Pandas

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("setupranali+http://localhost:8080?api_key=my-key")

# Load data into DataFrame
df = pd.read_sql("""
    SELECT region, product_category, SUM(amount) as revenue
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY region, product_category
""", engine)

print(df.head())
```

### Schema Introspection

```python
from sqlalchemy import create_engine, inspect

engine = create_engine("setupranali+http://localhost:8080?api_key=my-key")
inspector = inspect(engine)

# List all datasets (tables)
tables = inspector.get_table_names()
print("Datasets:", tables)

# Get columns for a dataset
columns = inspector.get_columns("orders")
for col in columns:
    print(f"  {col['name']}: {col['type']}")
```

### ORM Usage

```python
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.orm import declarative_base, Session

engine = create_engine("setupranali+http://localhost:8080?api_key=my-key")
Base = declarative_base()

# Note: SetuPranali is read-only, so ORM is mainly for querying
class Order(Base):
    __tablename__ = "orders"
    
    region = Column(String, primary_key=True)
    revenue = Column(Float)
    order_count = Column(Float)

with Session(engine) as session:
    # Query using ORM
    orders = session.query(Order).all()
    for order in orders:
        print(f"{order.region}: {order.revenue}")
```

## Superset Configuration

### Database Connection

```yaml
# Superset SQLAlchemy URI
SQLALCHEMY_DATABASE_URI: setupranali+http://setupranali:8080?api_key=your-key
```

### With Docker Compose

```yaml
services:
  superset:
    image: apache/superset
    environment:
      - SUPERSET_SECRET_KEY=your-secret
    depends_on:
      - setupranali
  
  setupranali:
    image: adeygifting/connector
    environment:
      - UBI_SECRET_KEY=your-secret
```

### Enable in Superset

Add to `superset_config.py`:

```python
# Allow SetuPranali dialect
ADDITIONAL_ALLOWED_ENGINES = ["setupranali"]

# Optional: Set default parameters
DEFAULT_SETUPRANALI_DATABASE = {
    "allow_ctas": False,
    "allow_cvas": False,
    "allow_dml": False,
    "allow_run_async": True,
}
```

## API Reference

### DB-API 2.0 Interface

```python
from sqlalchemy_setupranali import connect

# Direct connection (DB-API 2.0)
conn = connect(
    host="localhost",
    port=8080,
    api_key="your-key",
    scheme="http",
    database="orders"
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM orders LIMIT 10")
rows = cursor.fetchall()
cursor.close()
conn.close()
```

### Connection Class

```python
class SetuPranaliConnection:
    def cursor(self) -> SetuPranaliCursor
    def close() -> None
    def commit() -> None  # No-op (read-only)
    def rollback() -> None  # No-op (read-only)
```

### Cursor Class

```python
class SetuPranaliCursor:
    description: List[Tuple]  # Column descriptions
    rowcount: int  # Number of rows
    
    def execute(sql: str, parameters: Optional[Tuple] = None)
    def executemany(sql: str, seq_of_parameters: List[Tuple])
    def fetchone() -> Optional[Tuple]
    def fetchmany(size: int = None) -> List[Tuple]
    def fetchall() -> List[Tuple]
    def close() -> None
```

## Security

### Row-Level Security

SetuPranali enforces RLS automatically based on API key:

```python
# Each API key only sees authorized data
engine = create_engine("setupranali+http://localhost:8080?api_key=tenant-a-key")

# Queries automatically filtered by tenant
result = conn.execute(text("SELECT * FROM orders"))  # Only Tenant A's data
```

### Best Practices

1. **Use HTTPS in production**
   ```
   setupranali+https://bi-api.company.com?api_key=key
   ```

2. **Store API keys securely**
   ```python
   import os
   api_key = os.environ["SETUPRANALI_API_KEY"]
   engine = create_engine(f"setupranali+http://localhost:8080?api_key={api_key}")
   ```

3. **Use read-only API keys**

## Troubleshooting

### Connection Failed

```
OperationalError: Connection failed
```

**Solutions:**
1. Verify SetuPranali server is running
2. Check host and port are correct
3. Verify API key is valid
4. Check network/firewall settings

### Authentication Error

```
DatabaseError: 401 Unauthorized
```

**Solutions:**
1. Verify API key is correct
2. Ensure API key has access to requested dataset
3. Check API key hasn't expired

### Query Timeout

```
OperationalError: Query timeout after 30s
```

**Solutions:**
1. Increase timeout: `?timeout=60`
2. Add filters to reduce data volume
3. Use aggregations to reduce result size

## Development

### Setup

```bash
git clone https://github.com/setupranali/setupranali.github.io.git
cd packages/sqlalchemy-setupranali

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/
```

### Code Quality

```bash
black sqlalchemy_setupranali/
mypy sqlalchemy_setupranali/
```

## License

Apache 2.0 - See [LICENSE](../../LICENSE)

## Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Apache Superset](https://superset.apache.org/)
- [SetuPranali Documentation](https://setupranali.github.io/)
- [DB-API 2.0 Specification](https://peps.python.org/pep-0249/)

