# ClickHouse Examples

Connect SetuPranali to ClickHouse for blazing-fast analytics.

## Overview

ClickHouse excels at:
- Real-time analytics
- High-volume data ingestion
- Aggregation queries
- Time-series data

## Connection Configuration

### Basic Connection

```yaml
sources:
  clickhouse_db:
    type: clickhouse
    connection:
      host: localhost
      port: 9000
      database: analytics
      user: ${CLICKHOUSE_USER}
      password: ${CLICKHOUSE_PASSWORD}
```

### ClickHouse Cloud

```yaml
sources:
  clickhouse_cloud:
    type: clickhouse
    connection:
      host: xyz.clickhouse.cloud
      port: 9440
      database: default
      user: ${CLICKHOUSE_USER}
      password: ${CLICKHOUSE_PASSWORD}
      secure: true
```

### HTTP Interface

```yaml
sources:
  clickhouse_http:
    type: clickhouse
    connection:
      host: localhost
      port: 8123
      protocol: http
      database: analytics
      user: ${CLICKHOUSE_USER}
      password: ${CLICKHOUSE_PASSWORD}
```

## ClickHouse-Specific Features

### Array Functions

```yaml
dimensions:
  - name: tags_count
    type: number
    sql: length(tags)
    
  - name: first_tag
    type: string
    sql: tags[1]
    
  - name: has_premium_tag
    type: boolean
    sql: has(tags, 'premium')
```

### Date/Time Functions

```yaml
dimensions:
  - name: event_hour
    type: number
    sql: toHour(event_time)
    
  - name: event_date
    type: date
    sql: toDate(event_time)
    
  - name: event_week
    type: string
    sql: toYYYYMM(toMonday(event_time))
```

### Approximate Functions

```yaml
metrics:
  - name: unique_users_approx
    type: custom
    sql: uniqHLL12(user_id)
    
  - name: median_amount
    type: custom
    sql: quantile(0.5)(amount)
```

## Sample Dataset

```yaml
datasets:
  events:
    name: "Events"
    description: "Real-time event stream"
    source: clickhouse_db
    table: events
    
    dimensions:
      - name: event_date
        type: date
        sql: toDate(event_time)
        
      - name: event_hour
        type: number
        sql: toHour(event_time)
        
      - name: event_name
        type: string
        sql: event_name
        
      - name: user_id
        type: string
        sql: user_id
        
      - name: country
        type: string
        sql: country
    
    metrics:
      - name: event_count
        type: count
        sql: event_id
        
      - name: unique_users
        type: count_distinct
        sql: user_id
        
      - name: events_per_user
        type: custom
        sql: count() / uniq(user_id)
```

## Performance Tips

1. **Use MergeTree Engine** - Best for analytics workloads
2. **Partition by Date** - Always partition time-series data
3. **Use Approximate Functions** - `uniq`, `quantile` for large datasets
4. **Avoid SELECT *** - Only select needed columns
5. **Use PREWHERE** - For better filter performance

## Docker Setup

```yaml
version: '3.8'
services:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - clickhouse_data:/var/lib/clickhouse

  setupranali:
    image: adeygifting/connector:latest
    environment:
      - CLICKHOUSE_HOST=clickhouse
      - CLICKHOUSE_PORT=9000
```

