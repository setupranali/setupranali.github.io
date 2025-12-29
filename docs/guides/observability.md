# Observability

Monitor, trace, and audit your SetuPranali deployment with comprehensive observability features.

---

## Overview

SetuPranali provides four pillars of observability:

| Feature | Description |
|---------|-------------|
| **Query Analytics** | Dashboard for query patterns and performance |
| **Prometheus Metrics** | Export metrics for monitoring |
| **OpenTelemetry Tracing** | Distributed tracing support |
| **Audit Logs** | Full audit trail of all queries |

---

## Quick Start

Enable all observability features:

```bash
# Enable all features
ANALYTICS_ENABLED=true
METRICS_ENABLED=true
TRACING_ENABLED=true
AUDIT_ENABLED=true

# Optional: Configure endpoints
TRACING_ENDPOINT=http://jaeger:4317
AUDIT_LOG_FILE=/var/log/setupranali/audit.log
```

---

## Query Analytics

Track query patterns, performance, and usage across your deployment.

### Enable Analytics

```bash
ANALYTICS_ENABLED=true
ANALYTICS_RETENTION_HOURS=168  # 7 days
ANALYTICS_SAMPLE_RATE=1.0      # 100% sampling
```

### Analytics API

#### Get Overall Stats

```bash
curl http://localhost:8080/v1/analytics/stats
```

Response:

```json
{
  "total_queries": 15420,
  "total_errors": 23,
  "error_rate": 0.0015,
  "avg_duration_ms": 145.3,
  "avg_rows": 1250,
  "cache_hit_rate": 0.72,
  "by_dataset": {
    "orders": {"count": 8500, "duration_ms": 1200000, "errors": 12},
    "customers": {"count": 4200, "duration_ms": 450000, "errors": 5}
  },
  "slow_queries": [
    {"query_id": "abc123", "dataset": "orders", "duration_ms": 5200}
  ],
  "popular_dimensions": {
    "order_date": 8500,
    "region": 6200,
    "product_category": 4100
  },
  "popular_metrics": {
    "revenue": 12000,
    "order_count": 9500,
    "avg_order_value": 7200
  }
}
```

#### Get Hourly Stats

```bash
curl "http://localhost:8080/v1/analytics/hourly?hours=24"
```

Response:

```json
[
  {"hour": "2025-12-29-08", "count": 450, "avg_duration_ms": 132.5},
  {"hour": "2025-12-29-09", "count": 890, "avg_duration_ms": 145.2},
  {"hour": "2025-12-29-10", "count": 1200, "avg_duration_ms": 156.8}
]
```

#### Get Dataset Stats

```bash
curl http://localhost:8080/v1/analytics/datasets
```

Response:

```json
[
  {"dataset": "orders", "count": 8500, "avg_duration_ms": 141.2, "error_rate": 0.0014},
  {"dataset": "customers", "count": 4200, "avg_duration_ms": 107.1, "error_rate": 0.0012}
]
```

### Analytics Dashboard

Build dashboards with the analytics data:

```python
import requests
import pandas as pd

# Get hourly stats
response = requests.get("http://localhost:8080/v1/analytics/hourly?hours=168")
data = response.json()

df = pd.DataFrame(data)
df['hour'] = pd.to_datetime(df['hour'], format='%Y-%m-%d-%H')
df.plot(x='hour', y='count', title='Queries per Hour')
```

---

## Prometheus Metrics

Export metrics in Prometheus format for monitoring and alerting.

### Enable Metrics

```bash
METRICS_ENABLED=true
METRICS_PREFIX=setupranali
```

### Metrics Endpoint

```bash
curl http://localhost:8080/metrics
```

Response:

```
# HELP setupranali_queries_total Total number of queries
# TYPE setupranali_queries_total counter
setupranali_queries_total{dataset="orders"} 8500
setupranali_queries_total{dataset="customers"} 4200

# HELP setupranali_queries_error_total Total number of query errors
# TYPE setupranali_queries_error_total counter
setupranali_queries_error_total{dataset="orders"} 12

# HELP setupranali_query_duration_seconds Query duration histogram
# TYPE setupranali_query_duration_seconds histogram
setupranali_query_duration_seconds_bucket{dataset="orders",le="0.1"} 5200
setupranali_query_duration_seconds_bucket{dataset="orders",le="0.5"} 7800
setupranali_query_duration_seconds_bucket{dataset="orders",le="1.0"} 8400
setupranali_query_duration_seconds_bucket{dataset="orders",le="+Inf"} 8500
setupranali_query_duration_seconds_sum{dataset="orders"} 1200.5
setupranali_query_duration_seconds_count{dataset="orders"} 8500

# HELP setupranali_cache_size_bytes Current cache size
# TYPE setupranali_cache_size_bytes gauge
setupranali_cache_size_bytes 1048576

# HELP setupranali_active_connections Active connections
# TYPE setupranali_active_connections gauge
setupranali_active_connections 45
```

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `queries_total` | Counter | Total queries executed |
| `queries_success_total` | Counter | Successful queries |
| `queries_error_total` | Counter | Failed queries |
| `queries_cache_hits_total` | Counter | Cache hits |
| `query_duration_seconds` | Histogram | Query latency |
| `query_rows_total` | Counter | Total rows returned |
| `http_requests_total` | Counter | HTTP requests |
| `http_request_duration_seconds` | Histogram | HTTP latency |
| `active_connections` | Gauge | Active connections |
| `cache_size_bytes` | Gauge | Cache size |

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'setupranali'
    static_configs:
      - targets: ['setupranali:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

Import this dashboard JSON for Grafana:

```json
{
  "title": "SetuPranali",
  "panels": [
    {
      "title": "Queries per Second",
      "type": "graph",
      "targets": [
        {"expr": "rate(setupranali_queries_total[5m])"}
      ]
    },
    {
      "title": "Query Latency (p99)",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.99, rate(setupranali_query_duration_seconds_bucket[5m]))"}
      ]
    },
    {
      "title": "Error Rate",
      "type": "singlestat",
      "targets": [
        {"expr": "rate(setupranali_queries_error_total[5m]) / rate(setupranali_queries_total[5m])"}
      ]
    },
    {
      "title": "Cache Hit Rate",
      "type": "gauge",
      "targets": [
        {"expr": "rate(setupranali_queries_cache_hits_total[5m]) / rate(setupranali_queries_total[5m])"}
      ]
    }
  ]
}
```

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: setupranali
    rules:
      - alert: HighErrorRate
        expr: rate(setupranali_queries_error_total[5m]) / rate(setupranali_queries_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High query error rate"
          
      - alert: SlowQueries
        expr: histogram_quantile(0.99, rate(setupranali_query_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p99 latency > 5s"
          
      - alert: LowCacheHitRate
        expr: rate(setupranali_queries_cache_hits_total[5m]) / rate(setupranali_queries_total[5m]) < 0.5
        for: 15m
        labels:
          severity: info
        annotations:
          summary: "Cache hit rate below 50%"
```

---

## OpenTelemetry Tracing

Distributed tracing for debugging and performance analysis.

### Enable Tracing

```bash
TRACING_ENABLED=true
TRACING_SAMPLE_RATE=1.0           # 100% sampling
TRACING_EXPORTER=otlp             # otlp, jaeger, zipkin
TRACING_ENDPOINT=http://jaeger:4317
TRACING_SERVICE_NAME=setupranali
```

### Trace Visualization

Traces show the full request lifecycle:

```
[setupranali] POST /v1/query (250ms)
├── [validate_request] (2ms)
├── [check_permissions] (5ms)
│   └── [evaluate_policies] (3ms)
├── [check_cache] (1ms) - cache_miss
├── [execute_query] (235ms)
│   ├── [build_sql] (5ms)
│   ├── [connect_to_source] (10ms)
│   └── [run_query] (220ms)
└── [cache_result] (2ms)
```

### Trace Attributes

Each span includes:

| Attribute | Description |
|-----------|-------------|
| `dataset` | Dataset being queried |
| `dimensions` | Requested dimensions |
| `metrics` | Requested metrics |
| `tenant_id` | Tenant identifier |
| `cache_hit` | Whether cache was hit |
| `rows_returned` | Number of rows |
| `sql` | Generated SQL (if enabled) |

### Jaeger Configuration

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  setupranali:
    image: adeygifting/connector
    environment:
      - TRACING_ENABLED=true
      - TRACING_ENDPOINT=http://jaeger:4317
```

### Zipkin Configuration

```bash
TRACING_EXPORTER=zipkin
TRACING_ENDPOINT=http://zipkin:9411/api/v2/spans
```

### Custom Spans

Add custom spans in your code:

```python
from app.observability import get_tracer, trace

# Using context manager
tracer = get_tracer()
with tracer.start_span("custom_operation") as span:
    span.set_attribute("custom_key", "value")
    # ... your code ...

# Using decorator
@trace("my_function")
def my_function():
    pass
```

---

## Audit Logs

Complete audit trail of all queries and administrative actions.

### Enable Audit Logging

```bash
AUDIT_ENABLED=true
AUDIT_LOG_FILE=/var/log/setupranali/audit.log
AUDIT_INCLUDE_QUERY_TEXT=true
AUDIT_INCLUDE_RESULTS=false  # Don't log result data
```

### Audit Log Format

```json
{
  "event_id": "abc123def456",
  "timestamp": "2025-12-29T10:30:00.000Z",
  "event_type": "query",
  "api_key_hash": "a1b2c3d4e5f6g7h8",
  "user_id": "user@company.com",
  "tenant_id": "tenant_123",
  "source_ip": "192.168.1.100",
  "user_agent": "Python/3.11",
  "resource_type": "dataset",
  "resource_id": "orders",
  "action": "query",
  "details": {
    "dataset": "orders",
    "dimensions": ["order_date", "region"],
    "metrics": ["revenue", "order_count"],
    "filters": {"region": "US"},
    "rows_returned": 150
  },
  "success": true,
  "duration_ms": 145.5,
  "request_id": "req_xyz789"
}
```

### Audit Event Types

| Event Type | Description |
|------------|-------------|
| `query` | Query executed |
| `login` | User login |
| `logout` | User logout |
| `api_key_created` | API key created |
| `api_key_revoked` | API key revoked |
| `source_created` | Data source added |
| `source_updated` | Data source modified |
| `source_deleted` | Data source removed |
| `permission_denied` | Access denied |
| `permission_granted` | Access granted |
| `config_changed` | Configuration modified |
| `error` | Error occurred |

### Query Audit Logs

```bash
# Get recent audit events
curl "http://localhost:8080/v1/audit/events?limit=100"

# Filter by event type
curl "http://localhost:8080/v1/audit/events?event_type=query"

# Filter by tenant
curl "http://localhost:8080/v1/audit/events?tenant_id=tenant_123"

# Filter by time range
curl "http://localhost:8080/v1/audit/events?start_time=2025-12-29T00:00:00Z&end_time=2025-12-29T23:59:59Z"
```

### Log Shipping

Ship logs to external systems:

#### Elasticsearch

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/setupranali/audit.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "setupranali-audit-%{+yyyy.MM.dd}"
```

#### Splunk

```yaml
# fluentd.conf
<source>
  @type tail
  path /var/log/setupranali/audit.log
  pos_file /var/log/fluentd/audit.log.pos
  tag setupranali.audit
  format json
</source>

<match setupranali.**>
  @type splunk_hec
  host splunk.company.com
  port 8088
  token YOUR_HEC_TOKEN
</match>
```

### Sensitive Data Handling

Sensitive fields are automatically redacted:

```bash
# Configure sensitive fields
AUDIT_SENSITIVE_FIELDS=password,secret,token,key,ssn
```

Example redaction:

```json
{
  "details": {
    "api_key": "[REDACTED]",
    "password": "[REDACTED]",
    "user_data": {
      "email": "user@company.com",
      "ssn": "[REDACTED]"
    }
  }
}
```

---

## Helm Configuration

```yaml
# values.yaml
observability:
  analytics:
    enabled: true
    retentionHours: 168
    sampleRate: 1.0
  
  metrics:
    enabled: true
    prefix: setupranali
    serviceMonitor:
      enabled: true
      interval: 15s
  
  tracing:
    enabled: true
    sampleRate: 0.1  # 10% in production
    exporter: otlp
    endpoint: http://jaeger-collector:4317
    serviceName: setupranali
  
  audit:
    enabled: true
    logFile: /var/log/setupranali/audit.log
    includeQueryText: true
    persistence:
      enabled: true
      size: 10Gi
```

---

## Docker Configuration

```yaml
# docker-compose.yml
services:
  setupranali:
    image: adeygifting/connector
    environment:
      # Analytics
      - ANALYTICS_ENABLED=true
      - ANALYTICS_RETENTION_HOURS=168
      
      # Metrics
      - METRICS_ENABLED=true
      - METRICS_PREFIX=setupranali
      
      # Tracing
      - TRACING_ENABLED=true
      - TRACING_ENDPOINT=http://jaeger:4317
      
      # Audit
      - AUDIT_ENABLED=true
      - AUDIT_LOG_FILE=/var/log/setupranali/audit.log
    volumes:
      - audit-logs:/var/log/setupranali
    ports:
      - "8080:8080"

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  jaeger:
    image: jaegertracing/all-in-one
    ports:
      - "16686:16686"
      - "4317:4317"

volumes:
  audit-logs:
```

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `ANALYTICS_ENABLED` | Enable query analytics | `true` |
| `ANALYTICS_RETENTION_HOURS` | Analytics data retention | `168` |
| `ANALYTICS_SAMPLE_RATE` | Sampling rate (0.0-1.0) | `1.0` |
| `METRICS_ENABLED` | Enable Prometheus metrics | `true` |
| `METRICS_PREFIX` | Metrics name prefix | `setupranali` |
| `TRACING_ENABLED` | Enable OpenTelemetry tracing | `true` |
| `TRACING_SAMPLE_RATE` | Trace sampling rate | `1.0` |
| `TRACING_EXPORTER` | Exporter type (otlp/jaeger/zipkin) | `otlp` |
| `TRACING_ENDPOINT` | Exporter endpoint | - |
| `TRACING_SERVICE_NAME` | Service name in traces | `setupranali` |
| `AUDIT_ENABLED` | Enable audit logging | `true` |
| `AUDIT_LOG_FILE` | Audit log file path | - |
| `AUDIT_INCLUDE_QUERY_TEXT` | Include query in logs | `true` |
| `AUDIT_INCLUDE_RESULTS` | Include results in logs | `false` |
| `AUDIT_SENSITIVE_FIELDS` | Fields to redact | `password,secret,token,key` |

---

## Best Practices

### Production Settings

```bash
# Lower sampling in production
TRACING_SAMPLE_RATE=0.1        # 10% of requests
ANALYTICS_SAMPLE_RATE=1.0      # Keep 100% for analytics

# Configure retention
ANALYTICS_RETENTION_HOURS=168  # 7 days

# Ship logs externally
AUDIT_LOG_FILE=/var/log/setupranali/audit.log
```

### Security

1. **Redact Sensitive Data**: Configure `AUDIT_SENSITIVE_FIELDS`
2. **Restrict Metrics Access**: Use authentication on `/metrics`
3. **Encrypt Logs**: Use encrypted storage for audit logs
4. **Limit Retention**: Set appropriate retention periods

### Performance

1. **Sample Traces**: Use `TRACING_SAMPLE_RATE=0.1` in production
2. **Async Logging**: Audit logs are written asynchronously
3. **Cache Metrics**: Metrics are aggregated in memory
4. **Limit History**: Configure retention to manage memory

