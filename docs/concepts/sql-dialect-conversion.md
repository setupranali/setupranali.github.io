# SQL Dialect Conversion

SetuPranali uses SQLGlot to automatically convert SQL queries between different database dialects.

---

## Overview

SQLGlot integration enables:

- **Cross-Dialect Compatibility** - Write queries once, run anywhere
- **Automatic Conversion** - Convert PostgreSQL SQL to Snowflake, BigQuery, etc.
- **SQL Validation** - Parse and validate SQL before execution
- **Safe Query Building** - Programmatic SQL generation prevents injection

---

## Supported Dialects

| Database | SQLGlot Dialect | Status |
|----------|----------------|--------|
| PostgreSQL | `postgres` | ✅ Full Support |
| MySQL | `mysql` | ✅ Full Support |
| Snowflake | `snowflake` | ✅ Full Support |
| BigQuery | `bigquery` | ✅ Full Support |
| Databricks | `spark` | ✅ Full Support |
| Redshift | `redshift` | ✅ Full Support |
| ClickHouse | `clickhouse` | ✅ Full Support |
| DuckDB | `duckdb` | ✅ Full Support |
| Trino/Presto | `trino` / `presto` | ✅ Full Support |
| SQL Server | `tsql` | ✅ Full Support |
| Oracle | `oracle` | ✅ Full Support |
| SQLite | `sqlite` | ✅ Full Support |
| TimescaleDB | `postgres` | ✅ Full Support |
| CockroachDB | `postgres` | ✅ Full Support |

---

## How It Works

### Automatic Dialect Detection

When you execute a query, SetuPranali:

1. **Detects Source Dialect** - From data source configuration
2. **Parses SQL** - Using SQLGlot's parser
3. **Converts to Target** - Transforms AST to target dialect
4. **Executes** - Runs converted SQL on target database

### Example

```python
# Original SQL (PostgreSQL style)
sql = "SELECT DATE_TRUNC('month', order_date) as month, SUM(revenue) FROM orders GROUP BY 1"

# Automatically converted to Snowflake
# SELECT DATE_TRUNC('month', order_date) AS month, SUM(revenue) FROM orders GROUP BY 1

# Automatically converted to BigQuery
# SELECT DATE_TRUNC(order_date, MONTH) AS month, SUM(revenue) FROM orders GROUP BY 1
```

---

## SQL Builder

The `SQLBuilder` class provides programmatic SQL generation:

```python
from app.sql_builder import SQLBuilder

# Create builder for target dialect
builder = SQLBuilder(dialect="snowflake")

# Build query
sql, params = builder.build_query(
    dimensions=["city", "region"],
    metrics={"total_revenue": "SUM(revenue)", "order_count": "COUNT(*)"},
    source_table="orders",
    filters={
        "and": [
            {"field": "order_date", "op": "gte", "value": "2024-01-01"},
            {"field": "status", "op": "eq", "value": "completed"}
        ]
    },
    group_by=["city", "region"],
    order_by=[("total_revenue", "DESC")],
    limit=100
)

# SQL is automatically in Snowflake dialect
print(sql)
# SELECT "city", "region", SUM(revenue) AS "total_revenue", COUNT(*) AS "order_count"
# FROM "orders"
# WHERE "order_date" >= ? AND "status" = ?
# GROUP BY "city", "region"
# ORDER BY "total_revenue" DESC
# LIMIT 100
```

---

## SQL Validation

SQLGlot validates SQL before execution:

```python
from app.sql_builder import SQLBuilder

# Validate SQL
is_valid, error = SQLBuilder.validate_sql(
    "SELECT * FROM orders WHERE revenue > 1000",
    dialect="postgres"
)

if not is_valid:
    print(f"SQL Error: {error}")
```

### Security Benefits

- **Prevents SQL Injection** - AST-based parsing catches malicious patterns
- **Validates Syntax** - Catches errors before execution
- **Blocks Dangerous Operations** - DDL/DML operations are rejected

---

## RLS Filter Application

SQLGlot is used to inject Row-Level Security filters:

```python
# Original query
sql = "SELECT city, SUM(revenue) FROM orders GROUP BY city"

# After RLS injection (for tenant "acme")
# WITH rls_filtered AS (
#     SELECT * FROM (
#         SELECT city, SUM(revenue) FROM orders GROUP BY city
#     ) AS user_query
#     WHERE tenant_id = 'acme'
# )
# SELECT * FROM rls_filtered
```

---

## Query Planner Integration

The Query Planner uses SQLGlot for:

- **SQL Generation** - Building queries from semantic components
- **Join Construction** - Creating JOIN clauses
- **Filter Conversion** - Converting filter objects to SQL
- **Measure Expression Parsing** - Validating metric expressions

---

## Best Practices

### 1. Use Semantic Queries When Possible

Semantic queries (`/v1/query`) automatically handle dialect conversion:

```bash
# Works with any dialect
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -d '{
    "dataset": "orders",
    "dimensions": [{"name": "city"}],
    "metrics": [{"name": "total_revenue"}]
  }'
```

### 2. Specify Dialect for Raw SQL

When using `/v1/sql`, the dialect is detected from the dataset's source:

```bash
# Dialect automatically detected from dataset source
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: your-key" \
  -d '{
    "sql": "SELECT city FROM orders",
    "dataset": "orders"
  }'
```

### 3. Test Dialect-Specific Features

Some features are dialect-specific:

- **Window Functions** - Syntax varies by dialect
- **Date Functions** - Different function names
- **String Functions** - Dialect-specific implementations

### 4. Use SQLBuilder for Complex Queries

For programmatic query building:

```python
builder = SQLBuilder(dialect="bigquery")
sql, params = builder.build_query(...)
```

---

## Limitations

### Not Supported

- **Stored Procedures** - Not converted
- **User-Defined Functions** - Dialect-specific
- **Dialect-Specific Extensions** - May not convert perfectly

### Partial Support

- **Window Functions** - Basic support, advanced features may vary
- **JSON Functions** - Syntax differences between dialects
- **Array Functions** - Limited conversion

---

## Migration Between Databases

SQLGlot makes it easy to migrate queries:

```python
import sqlglot

# Convert PostgreSQL to Snowflake
sql_pg = "SELECT DATE_TRUNC('month', created_at) FROM orders"
sql_sf = sqlglot.transpile(sql_pg, read="postgres", write="snowflake")[0]

# Convert Snowflake to BigQuery
sql_bq = sqlglot.transpile(sql_sf, read="snowflake", write="bigquery")[0]
```

---

## Troubleshooting

### Conversion Errors

If SQL conversion fails:

1. Check SQL syntax is valid
2. Verify dialect is supported
3. Review SQLGlot error message
4. Use semantic queries instead

### Performance

SQLGlot parsing adds minimal overhead:

- **Parse Time**: < 1ms for typical queries
- **Conversion Time**: < 5ms for complex queries
- **Cache**: Parsed ASTs are cached

---

## References

- [SQLGlot Documentation](https://github.com/tobymao/sqlglot)
- [Query Planner Guide](../guides/datasets.md)
- [SQL API Reference](../api-reference/sql.md)

