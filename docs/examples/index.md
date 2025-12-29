# Examples

Real-world examples and reference architectures.

---

## Integration Examples

<div class="grid cards" markdown>

-   :material-source-branch:{ .lg .middle } **dbt Integration**

    ---

    Use dbt models with SetuPranali.

    [:octicons-arrow-right-24: dbt Example](dbt.md)

-   :material-database-multiple:{ .lg .middle } **Multi-Source**

    ---

    Connect multiple databases in one deployment.

    [:octicons-arrow-right-24: Multi-Source](multi-source.md)

-   :material-office-building:{ .lg .middle } **Enterprise Setup**

    ---

    Production configuration for enterprise.

    [:octicons-arrow-right-24: Enterprise](enterprise.md)

</div>

---

## Sample Configurations

### Basic E-Commerce

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: public.orders
    
    dimensions:
      - name: order_date
        type: date
        expr: order_date
      - name: status
        type: string
        expr: status
      - name: region
        type: string
        expr: region
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
      - name: orders
        type: number
        expr: "COUNT(*)"
      - name: avg_order_value
        type: number
        expr: "AVG(amount)"
    
    rls:
      tenant_column: tenant_id
```

### SaaS Analytics

```yaml
datasets:
  - name: usage
    source: bigquery-prod
    table: analytics.daily_usage
    
    dimensions:
      - name: date
        type: date
        expr: usage_date
      - name: feature
        type: string
        expr: feature_name
      - name: plan
        type: string
        expr: subscription_plan
    
    metrics:
      - name: active_users
        type: number
        expr: "SUM(unique_users)"
      - name: events
        type: number
        expr: "SUM(event_count)"
      - name: avg_session_duration
        type: number
        expr: "AVG(session_seconds)"
    
    rls:
      tenant_column: org_id
    
    incremental:
      date_column: usage_date
```

### Financial Dashboard

```yaml
datasets:
  - name: transactions
    source: snowflake-prod
    table: FINANCE.TRANSACTIONS
    
    dimensions:
      - name: transaction_date
        type: date
        expr: TXN_DATE
      - name: category
        type: string
        expr: CATEGORY
      - name: account_type
        type: string
        expr: ACCOUNT_TYPE
    
    metrics:
      - name: total_amount
        type: number
        expr: "SUM(AMOUNT)"
      - name: transaction_count
        type: number
        expr: "COUNT(*)"
      - name: average_amount
        type: number
        expr: "AVG(AMOUNT)"
    
    rls:
      tenant_column: ORG_ID
```

---

## Architecture Patterns

### Single Tenant

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Power BI   │────▶│  Connector   │────▶│   Database   │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Multi-Tenant

```
┌──────────────┐
│  Tenant A    │──┐
├──────────────┤  │     ┌──────────────┐     ┌──────────────┐
│  Tenant B    │──┼────▶│  Connector   │────▶│   Database   │
├──────────────┤  │     │  (with RLS)  │     │  (shared)    │
│  Tenant C    │──┘     └──────────────┘     └──────────────┘
└──────────────┘
```

### Multi-Source

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   BI Tools   │────▶│  Connector   │────▶│  Snowflake   │
└──────────────┘     │              │     ├──────────────┤
                     │              │────▶│  PostgreSQL  │
                     │              │     ├──────────────┤
                     │              │────▶│  BigQuery    │
                     └──────────────┘     └──────────────┘
```

