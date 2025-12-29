# TimescaleDB Examples

Connect SetuPranali to TimescaleDB for time-series analytics.

## Overview

TimescaleDB extends PostgreSQL with:
- Hypertables for time-series data
- Continuous aggregates
- Compression
- Data retention policies

## Connection Configuration

### Basic Connection

```yaml
sources:
  timescale:
    type: timescaledb
    connection:
      host: localhost
      port: 5432
      database: metrics
      user: ${TIMESCALE_USER}
      password: ${TIMESCALE_PASSWORD}
```

### Timescale Cloud

```yaml
sources:
  timescale_cloud:
    type: timescaledb
    connection:
      host: your-service.tsdb.cloud.timescale.com
      port: 5432
      database: tsdb
      user: ${TIMESCALE_USER}
      password: ${TIMESCALE_PASSWORD}
      ssl_mode: require
```

## TimescaleDB-Specific Features

### Time Bucket Functions

```yaml
dimensions:
  - name: time_bucket_1h
    type: timestamp
    sql: time_bucket('1 hour', timestamp)
    
  - name: time_bucket_1d
    type: date
    sql: time_bucket('1 day', timestamp)::date
    
  - name: time_bucket_1w
    type: date
    sql: time_bucket('1 week', timestamp)::date
```

### Continuous Aggregates

Query pre-computed aggregates:

```yaml
datasets:
  hourly_metrics:
    source: timescale
    table: hourly_metrics_cagg  # Continuous aggregate
```

### First/Last Functions

```yaml
metrics:
  - name: first_value
    type: custom
    sql: first(value, timestamp)
    
  - name: last_value
    type: custom
    sql: last(value, timestamp)
```

### Interpolation

```yaml
metrics:
  - name: interpolated_value
    type: custom
    sql: interpolate(avg(value))
```

## Sample Dataset

```yaml
datasets:
  sensor_data:
    name: "Sensor Data"
    description: "IoT sensor readings"
    source: timescale
    table: sensor_readings
    
    dimensions:
      - name: timestamp
        type: timestamp
        sql: timestamp
        
      - name: time_hour
        type: timestamp
        sql: time_bucket('1 hour', timestamp)
        
      - name: time_day
        type: date
        sql: time_bucket('1 day', timestamp)::date
        
      - name: sensor_id
        type: string
        sql: sensor_id
        
      - name: location
        type: string
        sql: location
        
      - name: metric_type
        type: string
        sql: metric_type
    
    metrics:
      - name: avg_value
        type: avg
        sql: value
        
      - name: max_value
        type: max
        sql: value
        
      - name: min_value
        type: min
        sql: value
        
      - name: reading_count
        type: count
        sql: timestamp
        
      - name: latest_reading
        type: custom
        sql: last(value, timestamp)
```

## Docker Setup

```yaml
version: '3.8'
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=metrics
    ports:
      - "5432:5432"

  setupranali:
    image: adeygifting/connector:latest
    environment:
      - TIMESCALE_HOST=timescaledb
      - TIMESCALE_USER=postgres
      - TIMESCALE_PASSWORD=postgres
```

## Best Practices

1. **Use Hypertables** - Convert time-series tables to hypertables
2. **Create Continuous Aggregates** - For common time bucket queries
3. **Enable Compression** - Compress old data
4. **Set Retention Policies** - Automatically drop old data
5. **Time Bucket Queries** - Always use time_bucket for grouping

