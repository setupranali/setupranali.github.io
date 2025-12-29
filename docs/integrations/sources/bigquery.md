# BigQuery

Connect to Google BigQuery.

---

## Requirements

- Google Cloud project
- BigQuery API enabled
- Service account with BigQuery permissions

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bigquery-prod",
    "type": "bigquery",
    "connection": {
      "project_id": "my-project-123",
      "credentials_json": "{...service-account-key...}",
      "location": "US"
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `project_id` | GCP project ID | Required |
| `credentials_json` | Service account JSON key | Required |
| `location` | Dataset location | `US` |

---

## Authentication

### Service Account Key

1. Go to [GCP Console](https://console.cloud.google.com)
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Create or select a service account
4. Create key (JSON format)
5. Use the JSON content as `credentials_json`

### Required Roles

Assign these roles to the service account:

| Role | Purpose |
|------|---------|
| `roles/bigquery.dataViewer` | Read data |
| `roles/bigquery.jobUser` | Run queries |

```bash
# Grant roles
gcloud projects add-iam-policy-binding my-project \
  --member="serviceAccount:bi-connector@my-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding my-project \
  --member="serviceAccount:bi-connector@my-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: events
    source: bigquery-prod
    table: analytics.events
    
    dimensions:
      - name: event_name
        type: string
        expr: event_name
      
      - name: event_date
        type: date
        expr: DATE(event_timestamp)
    
    metrics:
      - name: event_count
        type: number
        expr: "COUNT(*)"
```

### Table Reference Formats

```yaml
# Dataset and table
table: analytics.events

# Full path
table: my-project.analytics.events
```

---

## BigQuery-Specific Features

### Partitioned Tables

For partitioned tables, use incremental refresh:

```yaml
datasets:
  - name: events
    source: bigquery-prod
    table: analytics.events
    
    incremental:
      date_column: _PARTITIONDATE
      partition_type: DAY
```

### Clustered Tables

Ensure queries use cluster columns for performance:

```yaml
dimensions:
  - name: user_id
    type: string
    expr: user_id  # Cluster column
```

---

## Cost Optimization

### Query Pricing

BigQuery charges per TB scanned. Minimize costs:

1. **Use connector caching** - reduces repeated queries
2. **Select specific columns** - dimensions/metrics only
3. **Use partitioned tables** - with incremental refresh
4. **Set query limits** - MAX_ROWS in config

### Monitoring Costs

```sql
-- Check query costs
SELECT
  user_email,
  SUM(total_bytes_billed) / POW(1024, 4) AS tb_billed
FROM `region-US`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY user_email;
```

---

## Troubleshooting

### Access Denied

```
403 Access Denied: Table my-project:analytics.events
```

**Solutions**:
1. Verify service account has `bigquery.dataViewer` role
2. Check table-level permissions
3. Verify project ID is correct

### Quota Exceeded

```
403 Quota exceeded
```

**Solutions**:
1. Check project quotas in GCP Console
2. Request quota increase
3. Enable connector caching to reduce queries

### Invalid Credentials

```
Invalid credentials
```

**Solutions**:
1. Verify JSON key is complete and valid
2. Re-download service account key
3. Check key hasn't been revoked

