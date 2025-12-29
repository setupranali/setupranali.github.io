# Oracle Database

Connect SetuPranali to Oracle Database, Oracle Cloud Autonomous Database (ATP/ADW), and Oracle Exadata.

---

## Overview

**Oracle Database** is ideal for:

- Enterprise mission-critical applications
- Oracle Cloud Infrastructure (OCI)
- Existing Oracle data warehouses
- Oracle Autonomous Database (ATP/ADW)
- High-performance OLAP workloads

!!! info "Oracle Cloud Support"
    SetuPranali supports Oracle Autonomous Transaction Processing (ATP) and Autonomous Data Warehouse (ADW) with wallet-based authentication.

---

## Prerequisites

Install the Oracle Python driver:

```bash
# Recommended (modern, thin client)
pip install oracledb

# Legacy (requires Oracle Client libraries)
pip install cx_Oracle
```

### Oracle Client (Optional)

For thick mode (required for some advanced features):

=== "macOS"

    ```bash
    # Download Instant Client from Oracle
    # https://www.oracle.com/database/technologies/instant-client.html
    
    # Unzip and set environment
    export ORACLE_HOME=/path/to/instantclient
    export DYLD_LIBRARY_PATH=$ORACLE_HOME
    ```

=== "Linux"

    ```bash
    # Install libaio
    sudo apt-get install libaio1
    
    # Download and extract Instant Client
    wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-basic-linux.zip
    unzip instantclient-basic-linux.zip
    
    # Set environment
    export LD_LIBRARY_PATH=/path/to/instantclient:$LD_LIBRARY_PATH
    ```

=== "Windows"

    Download Instant Client from [Oracle](https://www.oracle.com/database/technologies/instant-client.html) and add to PATH.

---

## Configuration

### Register via API

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-oracle",
    "type": "oracle",
    "connection": {
      "host": "oracle.company.com",
      "service_name": "ORCL",
      "user": "bi_user",
      "password": "secret"
    }
  }'
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `host` | ✅* | - | Server hostname or IP |
| `port` | | `1521` | Listener port |
| `service_name` | ✅* | - | Oracle service name |
| `sid` | | - | Oracle SID (alternative to service_name) |
| `dsn` | | - | Full DSN string (alternative to host/service) |
| `user` | ✅ | - | Username |
| `password` | ✅ | - | Password |
| `wallet_location` | | - | Path to Oracle Wallet directory |
| `wallet_password` | | - | Wallet password |
| `thick_mode` | | `false` | Use thick client mode |
| `lib_dir` | | - | Oracle Client library directory |
| `encoding` | | `UTF-8` | Character encoding |
| `connection_timeout` | | `30` | Connection timeout (seconds) |
| `query_timeout` | | `0` | Query timeout (0 = no limit) |
| `prefetch_rows` | | `1000` | Rows to prefetch |
| `arraysize` | | `1000` | Fetch array size |
| `pool_min` | | `1` | Minimum connection pool size |
| `pool_max` | | `5` | Maximum connection pool size |

*Either `dsn` or `host` + `service_name`/`sid` is required.

---

## Examples

### Basic Connection

```json
{
  "name": "oracle-prod",
  "type": "oracle",
  "connection": {
    "host": "oracle.company.com",
    "port": 1521,
    "service_name": "ORCL",
    "user": "bi_user",
    "password": "secure_password"
  }
}
```

### Easy Connect String

```json
{
  "name": "oracle-easy",
  "type": "oracle",
  "connection": {
    "dsn": "oracle.company.com:1521/ORCL",
    "user": "bi_user",
    "password": "secure_password"
  }
}
```

### Oracle Cloud ATP/ADW

```json
{
  "name": "oracle-atp",
  "type": "atp",
  "connection": {
    "dsn": "myatp_high",
    "user": "ADMIN",
    "password": "secure_password",
    "wallet_location": "/path/to/wallet"
  }
}
```

### Using SID

```json
{
  "name": "oracle-sid",
  "type": "oracle",
  "connection": {
    "host": "oracle.company.com",
    "port": 1521,
    "sid": "ORCL",
    "user": "bi_user",
    "password": "secure_password"
  }
}
```

### With Connection Pool

```json
{
  "name": "oracle-pooled",
  "type": "oracle",
  "connection": {
    "host": "oracle.company.com",
    "service_name": "ORCL",
    "user": "bi_user",
    "password": "secure_password",
    "pool_min": 2,
    "pool_max": 10
  }
}
```

### Thick Mode (Advanced Features)

```json
{
  "name": "oracle-thick",
  "type": "oracle",
  "connection": {
    "host": "oracle.company.com",
    "service_name": "ORCL",
    "user": "bi_user",
    "password": "secure_password",
    "thick_mode": true,
    "lib_dir": "/opt/oracle/instantclient"
  }
}
```

---

## Oracle Cloud Setup

### 1. Download Wallet

1. Go to Oracle Cloud Console
2. Navigate to your ATP/ADW instance
3. Click "DB Connection"
4. Download the wallet ZIP file
5. Extract to a secure location

### 2. Configure Connection

```json
{
  "name": "cloud-adw",
  "type": "adw",
  "connection": {
    "dsn": "mydb_high",
    "user": "ADMIN",
    "password": "your_password",
    "wallet_location": "/secure/path/wallet"
  }
}
```

The `dsn` value corresponds to TNS names in the wallet's `tnsnames.ora`:
- `mydb_high` - High priority, parallel queries
- `mydb_medium` - Medium priority
- `mydb_low` - Low priority, background jobs
- `mydb_tp` - Transaction Processing
- `mydb_tpurgent` - Urgent Transaction Processing

---

## Dataset Configuration

### catalog.yaml Example

```yaml
datasets:
  - id: sales
    name: Sales Analytics
    description: Sales data from Oracle
    source: my-oracle
    table: SALES.FACT_SALES
    dimensions:
      - name: region
        expr: REGION_NAME
      - name: product
        expr: PRODUCT_CATEGORY
      - name: date
        expr: SALE_DATE
        type: date
    metrics:
      - name: revenue
        expr: "SUM(AMOUNT)"
      - name: orders
        expr: "COUNT(*)"
      - name: avg_order_value
        expr: "AVG(AMOUNT)"
    rls:
      mode: tenant_column
      field: TENANT_ID
```

### Using Schema Prefix

```yaml
datasets:
  - id: customers
    source: my-oracle
    table: ANALYTICS.DIM_CUSTOMERS
    dimensions:
      - name: customer_id
      - name: name
      - name: segment
```

!!! note "Case Sensitivity"
    Oracle identifiers are uppercase by default. Use uppercase in your catalog unless you created objects with quoted identifiers.

---

## Performance Tips

### 1. Connection Pooling

Use connection pooling for better performance:

```json
{
  "pool_min": 2,
  "pool_max": 10
}
```

### 2. Increase Prefetch Size

For large result sets:

```json
{
  "prefetch_rows": 5000,
  "arraysize": 5000
}
```

### 3. Use Thin Mode

The default thin mode (oracledb) is faster for most use cases:

```json
{
  "thick_mode": false
}
```

### 4. Choose Right Service Level (Cloud)

For analytics, use `_high` or `_medium` service levels:

```json
{
  "dsn": "mydb_high"
}
```

### 5. Enable Query Caching

```yaml
# values.yaml (Helm)
config:
  cache:
    enabled: true
    ttl: 300
```

---

## Troubleshooting

### ORA-12154: TNS could not resolve

```
ORA-12154: TNS:could not resolve the connect identifier specified
```

**Solutions:**
1. Check service_name or sid is correct
2. Verify tnsnames.ora configuration
3. Use Easy Connect format: `host:port/service_name`
4. For cloud, ensure wallet is extracted correctly

### ORA-01017: Invalid username/password

```
ORA-01017: invalid username/password; logon denied
```

**Solutions:**
1. Verify username and password
2. For cloud, use ADMIN user initially
3. Check password hasn't expired
4. Verify user has CREATE SESSION privilege

### ORA-12541: No listener

```
ORA-12541: TNS:no listener
```

**Solutions:**
1. Verify host and port are correct
2. Check Oracle listener is running
3. Verify network connectivity
4. Check firewall rules

### Wallet Errors

```
DPY-6005: cannot connect to database
```

**Solutions:**
1. Verify wallet_location path is correct
2. Ensure wallet files exist (cwallet.sso, tnsnames.ora)
3. Check wallet permissions
4. Verify wallet hasn't expired

### Performance Issues

**Solutions:**
1. Increase prefetch_rows and arraysize
2. Use connection pooling
3. Add indexes on frequently queried columns
4. Use materialized views for complex aggregations

---

## Security

### Row-Level Security

SetuPranali automatically applies RLS:

```yaml
datasets:
  - id: sales
    rls:
      mode: tenant_column
      field: TENANT_ID
```

### Minimal Permissions

Grant only necessary permissions:

```sql
-- Create a read-only user
CREATE USER bi_user IDENTIFIED BY "secure_password";

-- Grant connect privilege
GRANT CREATE SESSION TO bi_user;

-- Grant read access to specific tables
GRANT SELECT ON schema_name.table_name TO bi_user;

-- Or grant read access to all tables in a schema
GRANT SELECT ANY TABLE TO bi_user;  -- Use with caution
```

### Wallet Security

For Oracle Cloud:
1. Store wallet in a secure location
2. Set restrictive permissions: `chmod 600 wallet/*`
3. Use wallet_password for additional security
4. Rotate wallet periodically

---

## CLI Usage

```bash
# Add Oracle source
setupranali sources add \
  --name my-oracle \
  --type oracle \
  --config '{"host":"oracle.example.com","service_name":"ORCL","user":"bi_user","password":"secret"}'

# Test connection
setupranali sources test my-oracle

# Query
setupranali query sales -d region -m revenue
```

---

## API Examples

### Query via REST

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue", "orders"],
    "limit": 100
  }'
```

### SQL with RLS

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: tenant-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT region, SUM(amount) as revenue FROM SALES.FACT_SALES GROUP BY region",
    "dataset": "sales"
  }'
```

---

## Type Aliases

| Alias | Use Case |
|-------|----------|
| `oracle` | Standard Oracle Database |
| `oracledb` | Alternative name |
| `oci` | Oracle Cloud Infrastructure |
| `atp` | Autonomous Transaction Processing |
| `adw` | Autonomous Data Warehouse |

