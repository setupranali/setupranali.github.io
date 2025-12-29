# SQLite Examples

The simplest way to get started with SetuPranali - no database server required!

## Overview

SQLite is perfect for:
- Local development and testing
- Small to medium datasets
- Embedded analytics
- Demo and POC environments

## Quick Start

```bash
docker-compose up -d
curl http://localhost:8080/v1/health
```

## Connection Configuration

### File-Based Database

```yaml
sources:
  sqlite_db:
    type: sqlite
    connection:
      database: /app/data/analytics.db
      read_only: true
```

### In-Memory Database

```yaml
sources:
  sqlite_memory:
    type: sqlite
    connection:
      database: ":memory:"
```

### With Performance Tuning

```yaml
sources:
  sqlite_db:
    type: sqlite
    connection:
      database: /app/data/analytics.db
      read_only: true
      journal_mode: WAL
      cache_size: 10000
      synchronous: NORMAL
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: sqlite_db
    table: orders
    
    dimensions:
      - name: order_date
        type: date
        sql: order_date
        
      - name: order_month
        type: string
        sql: strftime('%Y-%m', order_date)
        
      - name: status
        type: string
        sql: status
    
    metrics:
      - name: revenue
        type: sum
        sql: amount
        
      - name: orders
        type: count
        sql: order_id
```

## SQLite-Specific Functions

```yaml
dimensions:
  # Date formatting
  - name: day_name
    type: string
    sql: |
      CASE CAST(strftime('%w', order_date) AS INTEGER)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
      END
      
  # String operations
  - name: email_domain
    type: string
    sql: substr(email, instr(email, '@') + 1)
```

## Files

```
sqlite/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── data/
│   └── orders.db
└── queries/
    └── sample.json
```

## Best Practices

1. **Use Read-Only Mode** for production to prevent accidental writes
2. **Enable WAL Mode** for better concurrent read performance
3. **Use Indexes** on frequently filtered columns
4. **Keep Files Small** - SQLite works best under 10GB

