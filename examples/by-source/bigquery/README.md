# BigQuery Examples

Complete examples for connecting SetuPranali to Google BigQuery.

## Overview

BigQuery is Google's serverless data warehouse. This example shows:
- Service account authentication
- Project and dataset configuration
- Cost-optimized querying

## Prerequisites

- Google Cloud project with BigQuery enabled
- Service account with BigQuery permissions
- Service account key (JSON)

## Connection Configuration

### Service Account Key File

```yaml
sources:
  bigquery_db:
    type: bigquery
    connection:
      project: your-gcp-project
      credentials_file: /path/to/service-account.json
      location: US
```

### Environment Variable (Recommended for Docker)

```yaml
sources:
  bigquery_db:
    type: bigquery
    connection:
      project: your-gcp-project
      # Uses GOOGLE_APPLICATION_CREDENTIALS env var
      location: US
```

### With Dataset Specification

```yaml
sources:
  bigquery_db:
    type: bigquery
    connection:
      project: your-gcp-project
      dataset: analytics
      credentials_file: /path/to/credentials.json
```

## BigQuery-Specific Features

### Partitioned Tables

```yaml
datasets:
  events:
    source: bigquery_db
    table: project.dataset.events
    partition_field: event_date
    
    dimensions:
      - name: event_date
        type: date
        sql: event_date
        description: "Partition key - always filter on this!"
```

### Nested/Repeated Fields

```yaml
dimensions:
  - name: user_country
    type: string
    sql: user.geo.country
    
  - name: first_event_param
    type: string
    sql: (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title')
```

### STRUCT and ARRAY

```yaml
dimensions:
  - name: item_names
    type: string
    sql: ARRAY_TO_STRING(ARRAY(SELECT name FROM UNNEST(items)), ', ')
```

## Sample Dataset

```yaml
datasets:
  ga4_events:
    name: "Google Analytics Events"
    description: "GA4 event data from BigQuery export"
    source: bigquery_db
    table: project.analytics_123456789.events_*
    
    dimensions:
      - name: event_date
        type: date
        sql: PARSE_DATE('%Y%m%d', event_date)
        
      - name: event_name
        type: string
        sql: event_name
        
      - name: platform
        type: string
        sql: platform
        
      - name: country
        type: string
        sql: geo.country
        
      - name: device_category
        type: string
        sql: device.category
    
    metrics:
      - name: event_count
        type: count
        sql: event_name
        
      - name: users
        type: count_distinct
        sql: user_pseudo_id
        
      - name: sessions
        type: count_distinct
        sql: CONCAT(user_pseudo_id, CAST(ga_session_id AS STRING))
```

## Cost Optimization

### Use Partitioned Tables

Always filter on partition columns:

```json
{
  "dataset": "ga4_events",
  "filters": [
    {
      "dimension": "event_date",
      "operator": ">=",
      "value": "2024-01-01"
    }
  ]
}
```

### Limit Scanned Data

```yaml
connection:
  maximum_bytes_billed: 1000000000  # 1 GB limit
```

### Use BI Engine

For frequently queried data, enable BI Engine reservation.

## IAM Permissions

Required roles for service account:
- `roles/bigquery.dataViewer` - Read access
- `roles/bigquery.jobUser` - Run queries

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/bigquery.jobUser"
```

## Docker Setup

```yaml
# docker-compose.yml
services:
  setupranali:
    image: adeygifting/connector:latest
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
      - BIGQUERY_PROJECT=your-project
    volumes:
      - ./credentials:/app/credentials:ro
      - ./catalog.yaml:/app/catalog.yaml:ro
```

## Files in This Example

```
bigquery/
├── README.md
├── catalog.yaml
├── docker-compose.yml
├── queries/
│   ├── daily-events.json
│   └── user-engagement.json
└── setup/
    └── create-service-account.sh
```

## Troubleshooting

### Permission Denied

Verify service account has correct roles and the key is valid.

### Query Exceeds Bytes Billed

Add `maximum_bytes_billed` to connection config or ensure partition filters.

### Table Not Found

Check project, dataset, and table names are correct (case-sensitive).

