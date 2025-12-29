# IoT & Sensor Data Example

Analytics for IoT and time-series sensor data with SetuPranali.

## Overview

This example covers:
- Time-series data modeling
- Sensor readings aggregation
- Real-time monitoring dashboards
- Alerting thresholds

## Quick Start

```bash
docker-compose up -d
```

## Data Model

```
┌─────────────┐     ┌─────────────┐
│   Devices   │────<│  Readings   │
└─────────────┘     └─────────────┘
       │
┌──────┴──────┐
│  Locations  │
└─────────────┘
```

## Catalog Configuration

```yaml
sources:
  timescale_db:
    type: timescaledb
    connection:
      host: ${DB_HOST}
      database: iot_data
      user: ${DB_USER}
      password: ${DB_PASSWORD}

datasets:
  sensor_readings:
    name: "Sensor Readings"
    description: "Raw sensor data from IoT devices"
    source: timescale_db
    table: sensor_readings
    
    dimensions:
      - name: timestamp
        type: timestamp
        sql: timestamp
        
      - name: time_bucket_1m
        type: timestamp
        sql: time_bucket('1 minute', timestamp)
        description: "1-minute aggregation"
        
      - name: time_bucket_1h
        type: timestamp
        sql: time_bucket('1 hour', timestamp)
        description: "Hourly aggregation"
        
      - name: time_bucket_1d
        type: date
        sql: time_bucket('1 day', timestamp)::date
        description: "Daily aggregation"
        
      - name: device_id
        type: string
        sql: device_id
        
      - name: sensor_type
        type: string
        sql: sensor_type
        description: "temperature, humidity, pressure, etc."
        
      - name: location_id
        type: string
        sql: location_id
        
      - name: unit
        type: string
        sql: unit
    
    metrics:
      - name: avg_value
        type: avg
        sql: value
        description: "Average sensor reading"
        
      - name: max_value
        type: max
        sql: value
        description: "Maximum reading"
        
      - name: min_value
        type: min
        sql: value
        description: "Minimum reading"
        
      - name: reading_count
        type: count
        sql: timestamp
        description: "Number of readings"
        
      - name: latest_value
        type: custom
        sql: last(value, timestamp)
        description: "Most recent reading"
        
      - name: value_stddev
        type: custom
        sql: STDDEV(value)
        description: "Standard deviation"

  devices:
    name: "Devices"
    description: "IoT device inventory"
    source: timescale_db
    table: devices
    
    dimensions:
      - name: device_id
        type: string
        sql: device_id
        primary_key: true
        
      - name: device_name
        type: string
        sql: name
        
      - name: device_type
        type: string
        sql: device_type
        
      - name: manufacturer
        type: string
        sql: manufacturer
        
      - name: install_date
        type: date
        sql: installed_at::date
        
      - name: location_id
        type: string
        sql: location_id
        
      - name: status
        type: string
        sql: status
        description: "online, offline, maintenance"
    
    metrics:
      - name: device_count
        type: count
        sql: device_id
        
      - name: online_devices
        type: count
        sql: CASE WHEN status = 'online' THEN device_id END

  locations:
    name: "Locations"
    source: timescale_db
    table: locations
    
    dimensions:
      - name: location_id
        type: string
        sql: location_id
        primary_key: true
        
      - name: location_name
        type: string
        sql: name
        
      - name: building
        type: string
        sql: building
        
      - name: floor
        type: string
        sql: floor
        
      - name: zone
        type: string
        sql: zone
        
      - name: latitude
        type: number
        sql: latitude
        
      - name: longitude
        type: number
        sql: longitude
    
    metrics:
      - name: location_count
        type: count
        sql: location_id

  # Pre-aggregated continuous aggregate
  hourly_stats:
    name: "Hourly Statistics"
    description: "Pre-computed hourly aggregations"
    source: timescale_db
    table: hourly_sensor_stats  # TimescaleDB continuous aggregate
    
    dimensions:
      - name: bucket
        type: timestamp
        sql: bucket
        
      - name: device_id
        type: string
        sql: device_id
        
      - name: sensor_type
        type: string
        sql: sensor_type
    
    metrics:
      - name: avg_value
        type: avg
        sql: avg_value
        
      - name: max_value
        type: max
        sql: max_value
        
      - name: min_value
        type: min
        sql: min_value
        
      - name: reading_count
        type: sum
        sql: reading_count
```

## Sample Queries

### Real-Time Dashboard

```json
{
  "dataset": "sensor_readings",
  "dimensions": ["device_id", "sensor_type"],
  "metrics": ["latest_value", "avg_value"],
  "filters": [
    {"dimension": "timestamp", "operator": ">=", "value": "now() - interval '5 minutes'"}
  ]
}
```

### Hourly Trends

```json
{
  "dataset": "sensor_readings",
  "dimensions": ["time_bucket_1h", "sensor_type"],
  "metrics": ["avg_value", "max_value", "min_value"],
  "filters": [
    {"dimension": "timestamp", "operator": ">=", "value": "2024-01-01"}
  ],
  "orderBy": [{"field": "time_bucket_1h", "direction": "asc"}]
}
```

### Device Status

```json
{
  "dataset": "devices",
  "dimensions": ["status", "device_type"],
  "metrics": ["device_count"]
}
```

### Anomaly Detection Query

```json
{
  "dataset": "sensor_readings",
  "dimensions": ["device_id", "time_bucket_1h"],
  "metrics": ["avg_value", "value_stddev"],
  "filters": [
    {"dimension": "sensor_type", "operator": "=", "value": "temperature"}
  ]
}
```

## TimescaleDB Setup

### Create Hypertable

```sql
CREATE TABLE sensor_readings (
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    location_id VARCHAR(50),
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20)
);

SELECT create_hypertable('sensor_readings', 'timestamp');
```

### Create Continuous Aggregate

```sql
CREATE MATERIALIZED VIEW hourly_sensor_stats
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    device_id,
    sensor_type,
    AVG(value) AS avg_value,
    MAX(value) AS max_value,
    MIN(value) AS min_value,
    COUNT(*) AS reading_count
FROM sensor_readings
GROUP BY bucket, device_id, sensor_type;

-- Auto-refresh policy
SELECT add_continuous_aggregate_policy('hourly_sensor_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### Compression

```sql
ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id'
);

SELECT add_compression_policy('sensor_readings', INTERVAL '7 days');
```

### Retention

```sql
SELECT add_retention_policy('sensor_readings', INTERVAL '1 year');
```

## Grafana Integration

This example works great with Grafana for real-time dashboards:

1. Install SetuPranali Grafana plugin
2. Add data source
3. Create dashboards with:
   - Time series panels
   - Gauge panels for current values
   - Alerting rules

## Files

```
iot/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   ├── hypertables.sql
│   └── sample-data.sql
├── queries/
│   └── sensor-queries.json
└── grafana/
    └── dashboard.json
```

