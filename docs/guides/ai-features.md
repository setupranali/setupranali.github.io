# AI-Powered Features

SetuPranali includes intelligent automation powered by AI and machine learning.

---

## Overview

| Feature | Description |
|---------|-------------|
| **Auto-generated Descriptions** | AI-powered documentation for metrics and dimensions |
| **Anomaly Detection** | Automatic alerts when metrics behave unusually |
| **Query Suggestions** | Smart autocomplete based on usage patterns |

---

## Quick Start

### Enable AI Features

```bash
# Enable all AI features
AI_ENABLED=true

# Use OpenAI for descriptions
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx

# Or use Anthropic
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Or use heuristics only (no API required)
AI_PROVIDER=none
```

---

## Auto-Generated Descriptions

Automatically generate documentation for metrics, dimensions, and datasets.

### How It Works

1. SetuPranali analyzes field metadata:
   - Field name and type
   - SQL expression
   - Sample values
   - Related fields

2. Generates business-focused descriptions using:
   - LLM (OpenAI/Anthropic) when configured
   - Smart heuristics as fallback

### API

```bash
# Get auto-generated description
curl "http://localhost:8080/v1/ai/describe" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "total_revenue",
    "type": "metric",
    "aggregation": "sum",
    "sql": "SUM(order_amount)"
  }'
```

Response:

```json
{
  "description": "Total sum of all order amounts, representing the complete revenue for the selected time period and dimensions."
}
```

### Bulk Generation

Generate descriptions for all fields in a dataset:

```bash
curl "http://localhost:8080/v1/ai/describe/dataset/orders" \
  -H "X-API-Key: your-key"
```

Response:

```json
{
  "dataset": {
    "name": "orders",
    "description": "Dataset containing order-level transaction data with revenue metrics and dimensional attributes."
  },
  "dimensions": [
    {
      "name": "order_date",
      "description": "Date when the order was placed, used for time-based analysis."
    },
    {
      "name": "region",
      "description": "Geographic region where the order originated."
    }
  ],
  "metrics": [
    {
      "name": "revenue",
      "description": "Total revenue from orders, calculated as sum of order amounts."
    },
    {
      "name": "order_count",
      "description": "Count of orders in the selected period."
    }
  ]
}
```

### Heuristic Patterns

When no LLM is configured, SetuPranali uses smart heuristics:

| Pattern | Generated Description |
|---------|----------------------|
| `total_*` | "Total sum of..." |
| `avg_*` | "Average value of..." |
| `count_*` | "Count of..." |
| `*_id` | "Unique identifier for..." |
| `*_date` | "Date of..." |
| `*_rate` | "Rate or percentage of..." |

---

## Anomaly Detection

Automatically detect unusual metric values and alert users.

### How It Works

1. SetuPranali tracks historical metric values
2. Calculates statistical baseline (mean, standard deviation)
3. Flags values that deviate significantly
4. Creates alerts with severity levels

### Alert Types

| Type | Description |
|------|-------------|
| `spike` | Value significantly higher than normal |
| `drop` | Value significantly lower than normal |
| `trend_change` | Significant change in trend direction |
| `missing_data` | Expected data not present |
| `outlier` | Value outside normal distribution |

### Severity Levels

| Severity | Standard Deviations |
|----------|---------------------|
| `low` | 2.0 - 2.5σ |
| `medium` | 2.5 - 3.0σ |
| `high` | 3.0 - 4.0σ |
| `critical` | > 4.0σ |

### API

#### Get Alerts

```bash
curl "http://localhost:8080/v1/ai/anomalies" \
  -H "X-API-Key: your-key"
```

Response:

```json
{
  "alerts": [
    {
      "id": "abc123",
      "metric": "revenue",
      "type": "spike",
      "severity": "high",
      "timestamp": "2025-12-29T10:30:00Z",
      "value": 150000,
      "expected_value": 50000,
      "deviation": 3.2,
      "description": "revenue is 3.2 standard deviations above normal. Current: 150000.00, Expected: 50000.00",
      "dimension_values": {
        "region": "US"
      },
      "acknowledged": false
    }
  ]
}
```

#### Filter Alerts

```bash
# By severity
curl "http://localhost:8080/v1/ai/anomalies?severity=critical"

# By metric
curl "http://localhost:8080/v1/ai/anomalies?metric=revenue"

# Unacknowledged only
curl "http://localhost:8080/v1/ai/anomalies?acknowledged=false"
```

#### Acknowledge Alert

```bash
curl -X POST "http://localhost:8080/v1/ai/anomalies/abc123/acknowledge" \
  -H "X-API-Key: your-key"
```

### Configuration

```bash
# Sensitivity (standard deviations for anomaly)
AI_ANOMALY_SENSITIVITY=2.0

# Minimum samples before detection starts
AI_ANOMALY_MIN_SAMPLES=10
```

### Webhooks

Configure webhooks to receive anomaly alerts:

```yaml
# catalog.yaml
ai:
  anomaly_webhooks:
    - url: https://slack.com/webhook/xxx
      severity: [high, critical]
    - url: https://pagerduty.com/webhook/xxx
      severity: [critical]
```

---

## Query Suggestions

Smart autocomplete based on usage patterns.

### How It Works

1. SetuPranali learns from query history
2. Tracks which dimensions/metrics are used together
3. Ranks suggestions by relevance
4. Adapts to each user's patterns

### API

#### Get Dimension Suggestions

```bash
curl "http://localhost:8080/v1/ai/suggest/dimensions" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "current_dimensions": ["order_date"],
    "current_metrics": ["revenue"],
    "prefix": ""
  }'
```

Response:

```json
{
  "suggestions": [
    {
      "type": "dimension",
      "value": "region",
      "display": "Region",
      "description": "Geographic region",
      "score": 0.95
    },
    {
      "type": "dimension",
      "value": "product_category",
      "display": "Product Category",
      "description": "Category of product",
      "score": 0.82
    }
  ]
}
```

#### Get Metric Suggestions

```bash
curl "http://localhost:8080/v1/ai/suggest/metrics" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "current_dimensions": ["order_date", "region"],
    "current_metrics": ["revenue"]
  }'
```

Response:

```json
{
  "suggestions": [
    {
      "type": "metric",
      "value": "order_count",
      "display": "Order Count",
      "score": 0.91
    },
    {
      "type": "metric",
      "value": "avg_order_value",
      "display": "Average Order Value",
      "score": 0.78
    }
  ]
}
```

#### Get Query Suggestions

```bash
curl "http://localhost:8080/v1/ai/suggest/queries?dataset=orders" \
  -H "X-API-Key: your-key"
```

Response:

```json
{
  "suggestions": [
    {
      "type": "query",
      "display": "revenue, order_count by order_date, region",
      "description": "Used 42 times",
      "score": 0.85,
      "metadata": {
        "dimensions": ["order_date", "region"],
        "metrics": ["revenue", "order_count"]
      }
    },
    {
      "type": "query",
      "display": "revenue by product_category",
      "description": "Used 28 times",
      "score": 0.72,
      "metadata": {
        "dimensions": ["product_category"],
        "metrics": ["revenue"]
      }
    }
  ]
}
```

### Scoring Algorithm

Suggestions are scored based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Usage Frequency** | 40% | How often the field is used |
| **Co-occurrence** | 60% | How often used with current selection |
| **Base Score** | 10% | Minimum relevance |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_ENABLED` | `true` | Enable AI features |
| `AI_PROVIDER` | `none` | LLM provider (openai, anthropic, none) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `AI_MODEL` | `gpt-4o-mini` | Model to use |
| `AI_AUTO_DESCRIPTIONS` | `true` | Enable auto descriptions |
| `AI_ANOMALY_DETECTION` | `true` | Enable anomaly detection |
| `AI_QUERY_SUGGESTIONS` | `true` | Enable query suggestions |
| `AI_ANOMALY_SENSITIVITY` | `2.0` | Standard deviations for anomaly |
| `AI_ANOMALY_MIN_SAMPLES` | `10` | Min samples for detection |

### Helm Configuration

```yaml
# values.yaml
ai:
  enabled: true
  provider: openai
  
  # From secret
  apiKeySecret: ai-api-keys
  
  autoDescriptions:
    enabled: true
    cacheHours: 24
  
  anomalyDetection:
    enabled: true
    sensitivity: 2.0
    minSamples: 10
    webhooks:
      - url: https://slack.com/webhook/xxx
        severity: [high, critical]
  
  querySuggestions:
    enabled: true
    maxHistory: 1000
```

### Catalog Configuration

```yaml
# catalog.yaml
ai:
  # Override descriptions
  descriptions:
    orders:
      revenue: "Total revenue from all completed orders"
      order_count: "Number of orders placed"
  
  # Anomaly detection settings
  anomaly:
    metrics:
      - revenue
      - order_count
    exclude_dimensions:
      - test_region
```

---

## Best Practices

### Auto Descriptions

1. **Review Generated Content**: Validate AI-generated descriptions
2. **Override When Needed**: Use catalog.yaml to set specific descriptions
3. **Provide Context**: Include SQL expressions and sample values

### Anomaly Detection

1. **Start Conservative**: Begin with higher sensitivity (3.0)
2. **Tune Over Time**: Adjust based on false positive rate
3. **Acknowledge Alerts**: Keep alert queue clean
4. **Set Up Webhooks**: Route critical alerts to on-call

### Query Suggestions

1. **Encourage Usage**: Suggestions improve with more queries
2. **Clean History**: Remove test queries from learning
3. **Per-Tenant Learning**: Consider tenant isolation

---

## Privacy & Security

- **No Data Sent to LLM**: Only metadata (names, types) is sent
- **API Keys Secured**: Stored as Kubernetes secrets
- **Local Fallback**: Works without external APIs
- **Audit Trail**: All AI operations are logged

