# CLI Tool

SetuPranali includes a powerful command-line interface for managing your semantic layer.

---

## Installation

=== "pip"

    ```bash
    # Install with CLI extras
    pip install setupranali[cli]
    ```

=== "From source"

    ```bash
    cd cli
    pip install -e .
    ```

---

## Quick Start

```bash
# Configure the CLI
setupranali config set url http://localhost:8080
setupranali config set api_key your-api-key

# Check server health
setupranali health

# List datasets
setupranali datasets list

# Run a query
setupranali query orders -d city -m revenue
```

---

## Commands Reference

### Global Options

| Option | Description |
|--------|-------------|
| `--url` | Server URL (or use `SETUPRANALI_URL` env) |
| `--api-key` | API key (or use `SETUPRANALI_API_KEY` env) |
| `--json` | Output as JSON |
| `--help` | Show help |

---

### `setupranali config`

Manage CLI configuration.

```bash
# Show current configuration
setupranali config show

# Set server URL
setupranali config set url http://localhost:8080

# Set API key
setupranali config set api_key pk_your_key_here

# Clear all configuration
setupranali config clear
```

---

### `setupranali health`

Check server health and status.

```bash
setupranali health
```

Example output:

```
╭─────────────────╮
│    HEALTHY      │
╰─────────────────╯

        Services        
┏━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Service     ┃ Status ┃
┡━━━━━━━━━━━━━╇━━━━━━━━┩
│ database    │ ✓      │
│ cache       │ ✓      │
│ sources_db  │ ✓      │
└─────────────┴────────┘
```

---

### `setupranali sources`

Manage data sources.

```bash
# List all sources
setupranali sources list

# Add a new source
setupranali sources add \
  --name my-postgres \
  --type postgres \
  --config '{"host":"localhost","port":5432,"database":"mydb","user":"user","password":"pass"}'

# Test connection
setupranali sources test my-postgres
```

Supported source types:

- `postgres`
- `mysql`
- `snowflake`
- `bigquery`
- `databricks`
- `redshift`
- `clickhouse`
- `duckdb`

---

### `setupranali datasets`

Manage datasets.

```bash
# List all datasets
setupranali datasets list

# Show dataset details
setupranali datasets show orders

# Validate catalog.yaml
setupranali datasets validate
setupranali datasets validate --catalog /path/to/catalog.yaml
```

Example output for `datasets show`:

```
╭─────────────────────────────╮
│ Orders                      │
│ Order-level transaction data│
╰─────────────────────────────╯

      Dimensions       
┏━━━━━━━━━┳━━━━━━━━┳━━━━━┓
┃ Name    ┃ Type   ┃ Desc┃
┡━━━━━━━━━╇━━━━━━━━╇━━━━━┩
│ city    │ string │     │
│ region  │ string │     │
│ product │ string │     │
└─────────┴────────┴─────┘

        Metrics        
┏━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name      ┃ Type   ┃ Expression  ┃
┡━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━┩
│ revenue   │ number │ SUM(amount) │
│ orders    │ number │ COUNT(*)    │
└───────────┴────────┴─────────────┘
```

---

### `setupranali query`

Execute semantic queries.

```bash
# Basic query
setupranali query orders -d city -m revenue

# Multiple dimensions and metrics
setupranali query orders -d city -d region -m revenue -m orders --limit 20

# Output formats
setupranali query orders -d city -m revenue --format table  # default
setupranali query orders -d city -m revenue --format json
setupranali query orders -d city -m revenue --format csv
```

Options:

| Option | Short | Description |
|--------|-------|-------------|
| `--dimensions` | `-d` | Dimensions to include (repeatable) |
| `--metrics` | `-m` | Metrics to include (repeatable) |
| `--limit` | `-l` | Maximum rows (default: 10) |
| `--format` | | Output format: table, json, csv |

---

### `setupranali sql`

Execute SQL queries with automatic RLS.

```bash
# Execute SQL
setupranali sql "SELECT city, SUM(revenue) FROM orders GROUP BY city" -D orders

# CSV output
setupranali sql "SELECT * FROM orders LIMIT 100" -D orders --format csv
```

!!! note "Security"
    Only `SELECT` queries are allowed. RLS is automatically applied based on your API key.

---

### `setupranali nlq`

Ask questions in natural language.

```bash
# Simple translation
setupranali nlq "What are the top 10 cities by revenue?" -D orders

# Execute the translated query
setupranali nlq "Show me monthly sales" -D sales -x

# Use AI provider
setupranali nlq "Total orders per region" -D orders -p openai -x
```

Options:

| Option | Short | Description |
|--------|-------|-------------|
| `--dataset` | `-D` | Dataset to query (required) |
| `--provider` | `-p` | NLQ provider: simple, openai, anthropic |
| `--execute` | `-x` | Execute the translated query |

---

### `setupranali introspect`

Show full schema introspection.

```bash
setupranali introspect
```

---

### `setupranali cache`

Manage query cache.

```bash
# Show cache statistics
setupranali cache stats

# Clear cache
setupranali cache clear
setupranali cache clear -D orders  # Specific dataset
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SETUPRANALI_URL` | Server URL | `http://localhost:8080` |
| `SETUPRANALI_API_KEY` | API key | (none) |

---

## Configuration File

The CLI stores configuration in `~/.setupranali/config.json`:

```json
{
  "url": "http://localhost:8080",
  "api_key": "pk_your_key_here"
}
```

**Configuration priority:**

1. Command-line flags (`--url`, `--api-key`)
2. Environment variables
3. Config file
4. Defaults

---

## CI/CD Integration

### Validate Catalog

```bash
# In CI pipeline
setupranali datasets validate --catalog ./catalog.yaml || exit 1
```

### Health Check

```bash
# In deployment scripts
setupranali health || exit 1
```

### Query for Monitoring

```bash
# Export metrics
setupranali --json query orders -d status -m count | jq '.rows'
```

---

## Scripting Examples

### Batch Export

```bash
#!/bin/bash
for dataset in orders sales customers; do
    setupranali query $dataset -d region -m total --format csv > "$dataset.csv"
done
```

### Health Monitoring

```bash
#!/bin/bash
if ! setupranali health > /dev/null 2>&1; then
    echo "SetuPranali is down!" | mail -s "Alert" admin@example.com
fi
```

---

## Troubleshooting

### Connection Errors

```
✗ Cannot connect to server
URL: http://localhost:8080
```

**Solutions:**

1. Check the server is running: `docker ps`
2. Verify the URL: `setupranali config show`
3. Check network connectivity

### Authentication Errors

```
Error ERR_1002
API key is invalid or expired
```

**Solutions:**

1. Verify your API key: `setupranali config show`
2. Update key: `setupranali config set api_key NEW_KEY`
3. Check key hasn't been revoked

### Dataset Not Found

```
Error ERR_2001
Dataset 'orderz' not found

💡 Suggestion: Did you mean: orders?
```

**Solutions:**

1. List available datasets: `setupranali datasets list`
2. Check spelling
3. Verify catalog.yaml is loaded

