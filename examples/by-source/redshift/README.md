# Amazon Redshift Examples

Connect SetuPranali to Amazon Redshift data warehouse.

## Overview

- Serverless and Provisioned cluster support
- IAM authentication
- Spectrum for S3 data

## Connection Configuration

### IAM Authentication (Recommended)

```yaml
sources:
  redshift:
    type: redshift
    connection:
      host: your-cluster.region.redshift.amazonaws.com
      port: 5439
      database: analytics
      user: ${REDSHIFT_USER}
      iam_role: arn:aws:iam::123456789:role/RedshiftRole
      cluster_id: your-cluster
      region: us-east-1
```

### Password Authentication

```yaml
sources:
  redshift:
    type: redshift
    connection:
      host: your-cluster.region.redshift.amazonaws.com
      port: 5439
      database: analytics
      user: ${REDSHIFT_USER}
      password: ${REDSHIFT_PASSWORD}
      ssl: true
```

### Redshift Serverless

```yaml
sources:
  redshift_serverless:
    type: redshift
    connection:
      host: workgroup.account.region.redshift-serverless.amazonaws.com
      port: 5439
      database: dev
      user: ${REDSHIFT_USER}
      password: ${REDSHIFT_PASSWORD}
```

## Redshift-Specific Features

### Window Functions

```yaml
metrics:
  - name: running_total
    type: custom
    sql: SUM(amount) OVER (ORDER BY order_date ROWS UNBOUNDED PRECEDING)
```

### Spectrum (Query S3)

```yaml
datasets:
  external_logs:
    source: redshift
    table: spectrum_schema.s3_logs
```

### Distribution and Sort Keys

Optimize queries by understanding table distribution:

```sql
SELECT * FROM pg_table_def WHERE tablename = 'orders';
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: redshift
    table: analytics.orders
    
    dimensions:
      - name: order_id
        type: string
        sql: order_id
        
      - name: order_date
        type: date
        sql: order_date
        
      - name: order_month
        type: string
        sql: TO_CHAR(order_date, 'YYYY-MM')
        
      - name: region
        type: string
        sql: region
    
    metrics:
      - name: revenue
        type: sum
        sql: total_amount
        
      - name: orders
        type: count
        sql: order_id

cache:
  enabled: true
  ttl: 300
```

## Performance Tips

1. **Use Sort Keys** - Query on sort key columns when possible
2. **Leverage Distribution** - Understand table distribution for JOINs
3. **ANALYZE Command** - Keep statistics updated
4. **Avoid Cross-AZ** - Keep compute and storage in same AZ
5. **Use Result Caching** - Redshift caches query results automatically

## VPC Configuration

For Redshift in VPC:
1. Ensure SetuPranali can reach Redshift endpoint
2. Security group allows inbound on port 5439
3. Consider VPC endpoints for private connectivity

