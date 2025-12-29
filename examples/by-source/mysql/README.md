# MySQL Examples

Complete examples for connecting SetuPranali to MySQL.

## Overview

This example demonstrates:
- Connecting SetuPranali to MySQL/MariaDB
- Defining semantic datasets
- Common MySQL-specific configurations

## Quick Start

```bash
# Start the environment
docker-compose up -d

# Verify connection
curl http://localhost:8080/v1/health

# Run a query
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer demo_key" \
  -H "Content-Type: application/json" \
  -d @queries/sales-summary.json
```

## Connection Configuration

### Basic Connection

```yaml
sources:
  mysql_db:
    type: mysql
    connection:
      host: localhost
      port: 3306
      database: analytics
      user: ${MYSQL_USER}
      password: ${MYSQL_PASSWORD}
```

### With SSL/TLS

```yaml
sources:
  mysql_db:
    type: mysql
    connection:
      host: your-db.example.com
      port: 3306
      database: analytics
      user: ${MYSQL_USER}
      password: ${MYSQL_PASSWORD}
      ssl: true
      ssl_ca: /path/to/ca-cert.pem
      ssl_cert: /path/to/client-cert.pem
      ssl_key: /path/to/client-key.pem
```

### Amazon RDS MySQL

```yaml
sources:
  rds_mysql:
    type: mysql
    connection:
      host: your-instance.region.rds.amazonaws.com
      port: 3306
      database: analytics
      user: ${RDS_USER}
      password: ${RDS_PASSWORD}
      ssl: true
      ssl_ca: /path/to/rds-ca-2019-root.pem
```

### Connection Pool Settings

```yaml
sources:
  mysql_db:
    type: mysql
    connection:
      host: localhost
      port: 3306
      database: analytics
      user: ${MYSQL_USER}
      password: ${MYSQL_PASSWORD}
      pool_size: 10
      pool_recycle: 3600
      connect_timeout: 10
```

## MySQL-Specific SQL Functions

### Date Functions

```yaml
dimensions:
  - name: order_month
    type: string
    sql: DATE_FORMAT(order_date, '%Y-%m')
    
  - name: order_year
    type: number
    sql: YEAR(order_date)
    
  - name: day_of_week
    type: string
    sql: DAYNAME(order_date)
    
  - name: quarter
    type: string
    sql: CONCAT('Q', QUARTER(order_date))
```

### String Functions

```yaml
dimensions:
  - name: customer_name_upper
    type: string
    sql: UPPER(customer_name)
    
  - name: email_domain
    type: string
    sql: SUBSTRING_INDEX(email, '@', -1)
```

### Conditional Logic

```yaml
dimensions:
  - name: order_size
    type: string
    sql: |
      CASE 
        WHEN amount < 50 THEN 'Small'
        WHEN amount < 200 THEN 'Medium'
        ELSE 'Large'
      END

metrics:
  - name: delivered_revenue
    type: custom
    sql: SUM(IF(status = 'delivered', amount, 0))
```

## Files in This Example

```
mysql/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   └── init.sql
└── queries/
    ├── sales-summary.json
    └── monthly-trends.json
```

## Troubleshooting

### Access Denied Error

```sql
-- Grant permissions
GRANT SELECT ON analytics.* TO 'user'@'%';
FLUSH PRIVILEGES;
```

### Connection Timeout

```yaml
connection:
  connect_timeout: 30
  read_timeout: 60
```

### Character Set Issues

```yaml
connection:
  charset: utf8mb4
  collation: utf8mb4_unicode_ci
```

## Cleanup

```bash
docker-compose down -v
```

