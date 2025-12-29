# Natural Language Query API

Ask questions in plain English and get structured queries.

## Endpoint

```
POST /v1/nlq
```

## Authentication

Requires API key in header:
```
X-API-Key: your-api-key
```

---

## Request

```json
{
  "question": "What are the top 10 cities by revenue?",
  "dataset": "orders",
  "provider": "simple",
  "execute": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Natural language question |
| `dataset` | string | Yes | Dataset to query |
| `provider` | string | No | `simple`, `openai`, or `anthropic` (default: `simple`) |
| `model` | string | No | Model name for AI providers |
| `execute` | boolean | No | Execute the translated query (default: `false`) |

---

## Response

```json
{
  "question": "What are the top 10 cities by revenue?",
  "query": {
    "dimensions": ["city"],
    "metrics": ["total_revenue"],
    "filters": [],
    "orderBy": [{"field": "total_revenue", "direction": "desc"}],
    "limit": 10
  },
  "explanation": "Show total revenue grouped by city, sorted by revenue descending, limited to top 10",
  "confidence": 0.85,
  "suggestions": [],
  "provider": "simple",
  "results": {
    "columns": [
      {"name": "city", "type": "string"},
      {"name": "total_revenue", "type": "number"}
    ],
    "data": [
      {"city": "Mumbai", "total_revenue": 150000},
      {"city": "Delhi", "total_revenue": 120000}
    ],
    "rowCount": 10
  }
}
```

---

## Providers

### Simple (Rule-Based)

No AI required. Uses pattern matching for common queries.

```json
{
  "question": "Top 10 cities by revenue",
  "dataset": "orders",
  "provider": "simple"
}
```

**Supported Patterns:**
- "top N by metric"
- "total/sum/average of metric"
- "group by dimension"
- "highest/lowest metric"

### OpenAI

Requires `OPENAI_API_KEY` environment variable.

```json
{
  "question": "Show me monthly revenue trends for the last quarter",
  "dataset": "orders",
  "provider": "openai",
  "model": "gpt-3.5-turbo"
}
```

### Anthropic

Requires `ANTHROPIC_API_KEY` environment variable.

```json
{
  "question": "Compare revenue between cities",
  "dataset": "orders",
  "provider": "anthropic",
  "model": "claude-3-haiku-20240307"
}
```

---

## Examples

### Basic Question

```bash
curl -X POST http://localhost:8080/v1/nlq \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "question": "What are the top 5 products by sales?",
    "dataset": "orders",
    "provider": "simple",
    "execute": true
  }'
```

### Complex Question (AI)

```bash
curl -X POST http://localhost:8080/v1/nlq \
  -H "X-API-Key: your-api-key" \
  -d '{
    "question": "Show me the month-over-month revenue growth for each region in Q4 2024",
    "dataset": "orders",
    "provider": "openai",
    "execute": true
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/nlq",
    headers={"X-API-Key": "your-api-key"},
    json={
        "question": "Which customers have the highest order values?",
        "dataset": "orders",
        "execute": True
    }
)

result = response.json()
print(f"Explanation: {result['explanation']}")
print(f"Confidence: {result['confidence']}")

if "results" in result:
    for row in result["results"]["data"]:
        print(row)
```

### JavaScript Example

```javascript
const response = await fetch('http://localhost:8080/v1/nlq', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    question: 'Show revenue by month for 2024',
    dataset: 'orders',
    provider: 'simple',
    execute: true
  })
});

const { query, explanation, results } = await response.json();
console.log('Translated query:', query);
console.log('Explanation:', explanation);
```

---

## Question Patterns

### Well-Understood Patterns

| Pattern | Example |
|---------|---------|
| Top N by metric | "Top 10 cities by revenue" |
| Totals | "Total revenue by product" |
| Comparisons | "Revenue by region" |
| Time-based | "Monthly sales for 2024" |
| Filtering | "Orders over $1000" |
| Aggregations | "Average order value by customer" |

### Tips for Better Results

1. **Be specific**: "Revenue by city" vs "Show me data"
2. **Use metric names**: Reference actual metric names from your dataset
3. **Specify limits**: "Top 10" vs "all cities"
4. **Include time ranges**: "Last 30 days" or "Q4 2024"

---

## Confidence Scores

| Score | Meaning |
|-------|---------|
| 0.9+ | High confidence, query likely correct |
| 0.7-0.9 | Good confidence, review recommended |
| 0.5-0.7 | Moderate confidence, verify query |
| <0.5 | Low confidence, question unclear |

---

## Error Handling

### Question Not Understood

```json
{
  "question": "asdfgh",
  "query": {},
  "explanation": "Could not understand the question",
  "confidence": 0.0,
  "suggestions": [
    "Show me total revenue by city",
    "What are the top 10 products by sales?"
  ]
}
```

### Missing AI Provider

```json
{
  "detail": "Provider 'openai' requires additional packages: No module named 'openai'"
}
```

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `NLQ_DEFAULT_PROVIDER` | Default provider (optional) |
| `NLQ_DEFAULT_MODEL` | Default model (optional) |

---

## Next Steps

- [Query API](query.md)
- [GraphQL API](graphql.md)
- [Schema Introspection](introspection.md)

