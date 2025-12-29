# SetuPranali CLI

Command-line interface for managing SetuPranali semantic BI layer.

## Installation

### From the main project

```bash
# Install with CLI extras
pip install setupranali[cli]
```

### Standalone installation

```bash
cd cli
pip install -e .
```

### Requirements

- Python 3.9+
- click
- httpx
- rich
- pyyaml

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
setupranali query orders -d city -m revenue --limit 10
```

## Commands

### Configuration

```bash
# Show current config
setupranali config show

# Set server URL
setupranali config set url http://localhost:8080

# Set API key
setupranali config set api_key pk_your_key_here

# Clear config
setupranali config clear
```

### Health Check

```bash
# Check server status
setupranali health

# JSON output
setupranali --json health
```

### Data Sources

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

### Datasets

```bash
# List all datasets
setupranali datasets list

# Show dataset details
setupranali datasets show orders

# Validate catalog.yaml
setupranali datasets validate
setupranali datasets validate --catalog /path/to/catalog.yaml
```

### Semantic Queries

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

### SQL Queries

```bash
# Execute SQL with automatic RLS
setupranali sql "SELECT city, SUM(revenue) FROM orders GROUP BY city" -D orders

# CSV output
setupranali sql "SELECT * FROM orders LIMIT 100" -D orders --format csv
```

### Natural Language Queries

```bash
# Simple rule-based translation
setupranali nlq "What are the top 10 cities by revenue?" -D orders

# Execute the translated query
setupranali nlq "Show me monthly sales" -D sales -x

# Use OpenAI for translation
setupranali nlq "Total orders per region" -D orders -p openai -x
```

### Schema Introspection

```bash
# Show full schema for all datasets
setupranali introspect

# JSON output
setupranali --json introspect
```

### Cache Management

```bash
# Show cache statistics
setupranali cache stats

# Clear cache (requires confirmation)
setupranali cache clear

# Clear specific dataset cache
setupranali cache clear -D orders
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SETUPRANALI_URL` | Server URL | `http://localhost:8080` |
| `SETUPRANALI_API_KEY` | API key for authentication | (none) |

## Output Formats

All commands support `--json` flag for JSON output:

```bash
setupranali --json datasets list
setupranali --json health
```

Query commands support multiple formats:

```bash
setupranali query orders -d city -m revenue --format table  # Rich table (default)
setupranali query orders -d city -m revenue --format json   # JSON
setupranali query orders -d city -m revenue --format csv    # CSV
```

## Configuration File

The CLI stores configuration in `~/.setupranali/config.json`:

```json
{
  "url": "http://localhost:8080",
  "api_key": "pk_your_key_here"
}
```

Configuration priority:
1. Command-line flags (`--url`, `--api-key`)
2. Environment variables (`SETUPRANALI_URL`, `SETUPRANALI_API_KEY`)
3. Config file (`~/.setupranali/config.json`)
4. Defaults

## Error Handling

The CLI displays structured errors with:
- Error code for searching logs
- Human-readable message
- Suggestion for fixing the issue
- Link to documentation

```
Error ERR_2001
Dataset 'orderz' not found

💡 Suggestion: Check that 'orderz' is defined in catalog.yaml. Did you mean: orders?
📚 Docs: https://setupranali.github.io/guides/datasets/
```

## Examples

### Complete Workflow

```bash
# 1. Configure
setupranali config set url http://localhost:8080
setupranali config set api_key pk_demo_key

# 2. Check health
setupranali health

# 3. Explore datasets
setupranali datasets list
setupranali datasets show orders

# 4. Run queries
setupranali query orders -d city -d region -m total_revenue -m order_count --limit 50

# 5. Ask questions
setupranali nlq "What regions have the highest revenue?" -D orders -x
```

### CI/CD Integration

```bash
# Validate catalog before deployment
setupranali datasets validate --catalog ./catalog.yaml

# Health check in deployment
setupranali health || exit 1

# Query for monitoring
setupranali --json query orders -d status -m count | jq '.rows'
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](../LICENSE) for details.

