# SaaS Metrics Example

A complete example for SaaS business analytics with SetuPranali.

## Overview

Track key SaaS metrics:
- MRR/ARR
- Churn & Retention
- Customer Lifetime Value
- Revenue per User

## Key Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| MRR | Monthly Recurring Revenue | Sum of monthly subscriptions |
| ARR | Annual Recurring Revenue | MRR × 12 |
| Churn Rate | Customer churn % | Lost customers / Start customers |
| Net Revenue Retention | Revenue retention | (MRR + Expansion - Churn) / Start MRR |
| LTV | Lifetime Value | ARPU / Churn Rate |
| CAC | Customer Acquisition Cost | Marketing spend / New customers |
| LTV:CAC | Ratio | LTV / CAC |

## Quick Start

```bash
docker-compose up -d
```

## Data Model

```
┌──────────────┐     ┌──────────────┐
│   Accounts   │────<│Subscriptions │
└──────────────┘     └──────────────┘
       │                    │
       │              ┌─────┴─────┐
       │              │  Invoices │
       │              └───────────┘
       │
┌──────┴───────┐
│    Events    │
└──────────────┘
```

## Catalog Configuration

```yaml
sources:
  saas_db:
    type: postgres
    connection:
      host: ${DB_HOST}
      database: saas_analytics
      user: ${DB_USER}
      password: ${DB_PASSWORD}

datasets:
  subscriptions:
    name: "Subscriptions"
    description: "Active and historical subscriptions"
    source: saas_db
    table: subscriptions
    
    dimensions:
      - name: subscription_id
        type: string
        sql: subscription_id
        primary_key: true
        
      - name: account_id
        type: string
        sql: account_id
        
      - name: plan_name
        type: string
        sql: plan_name
        
      - name: plan_tier
        type: string
        sql: plan_tier
        description: "Free, Starter, Pro, Enterprise"
        
      - name: billing_period
        type: string
        sql: billing_period
        description: "monthly, annual"
        
      - name: status
        type: string
        sql: status
        description: "active, cancelled, paused, trial"
        
      - name: start_date
        type: date
        sql: started_at::date
        
      - name: start_month
        type: string
        sql: TO_CHAR(started_at, 'YYYY-MM')
        
      - name: cancel_date
        type: date
        sql: cancelled_at::date
        
      - name: cancel_reason
        type: string
        sql: cancel_reason
    
    metrics:
      - name: mrr
        type: sum
        sql: CASE WHEN status = 'active' THEN mrr_amount ELSE 0 END
        description: "Monthly Recurring Revenue"
        format: "$,.2f"
        
      - name: arr
        type: custom
        sql: SUM(CASE WHEN status = 'active' THEN mrr_amount ELSE 0 END) * 12
        description: "Annual Recurring Revenue"
        format: "$,.2f"
        
      - name: active_subscriptions
        type: count
        sql: CASE WHEN status = 'active' THEN subscription_id END
        
      - name: new_mrr
        type: sum
        sql: CASE WHEN started_at >= DATE_TRUNC('month', CURRENT_DATE) THEN mrr_amount ELSE 0 END
        format: "$,.2f"
        
      - name: churned_mrr
        type: sum
        sql: CASE WHEN cancelled_at >= DATE_TRUNC('month', CURRENT_DATE) THEN mrr_amount ELSE 0 END
        format: "$,.2f"
        
      - name: avg_mrr_per_account
        type: custom
        sql: SUM(mrr_amount) / NULLIF(COUNT(DISTINCT account_id), 0)
        format: "$,.2f"

  accounts:
    name: "Accounts"
    description: "Customer accounts"
    source: saas_db
    table: accounts
    
    dimensions:
      - name: account_id
        type: string
        sql: account_id
        primary_key: true
        
      - name: company_name
        type: string
        sql: company_name
        
      - name: industry
        type: string
        sql: industry
        
      - name: company_size
        type: string
        sql: company_size
        description: "1-10, 11-50, 51-200, 201-1000, 1000+"
        
      - name: acquisition_source
        type: string
        sql: acquisition_source
        
      - name: signup_date
        type: date
        sql: created_at::date
        
      - name: signup_month
        type: string
        sql: TO_CHAR(created_at, 'YYYY-MM')
        
      - name: country
        type: string
        sql: country
        
      - name: is_churned
        type: boolean
        sql: churned_at IS NOT NULL
    
    metrics:
      - name: account_count
        type: count
        sql: account_id
        
      - name: active_accounts
        type: count
        sql: CASE WHEN churned_at IS NULL THEN account_id END
        
      - name: churned_accounts
        type: count
        sql: CASE WHEN churned_at IS NOT NULL THEN account_id END
        
      - name: total_ltv
        type: sum
        sql: lifetime_value
        format: "$,.2f"
        
      - name: avg_ltv
        type: avg
        sql: lifetime_value
        format: "$,.2f"

  mrr_movements:
    name: "MRR Movements"
    description: "Monthly MRR changes by type"
    source: saas_db
    sql: |
      SELECT 
        date_trunc('month', event_date)::date as month,
        movement_type,
        SUM(mrr_change) as mrr_amount,
        COUNT(DISTINCT account_id) as account_count
      FROM mrr_events
      GROUP BY 1, 2
    
    dimensions:
      - name: month
        type: date
        sql: month
        
      - name: movement_type
        type: string
        sql: movement_type
        description: "new, expansion, contraction, churn, reactivation"
    
    metrics:
      - name: mrr_amount
        type: sum
        sql: mrr_amount
        format: "$,.2f"
        
      - name: account_count
        type: sum
        sql: account_count

  product_usage:
    name: "Product Usage"
    description: "Feature usage and engagement"
    source: saas_db
    table: usage_events
    
    dimensions:
      - name: event_date
        type: date
        sql: event_date
        
      - name: account_id
        type: string
        sql: account_id
        
      - name: feature
        type: string
        sql: feature_name
        
      - name: plan_tier
        type: string
        sql: plan_tier
    
    metrics:
      - name: event_count
        type: count
        sql: event_id
        
      - name: active_users
        type: count_distinct
        sql: user_id
        
      - name: active_accounts
        type: count_distinct
        sql: account_id

# Multi-tenant SaaS
rls:
  subscriptions:
    field: partner_id
    operator: "="
  accounts:
    field: partner_id
    operator: "="
```

## Sample Queries

### MRR by Month

```json
{
  "dataset": "subscriptions",
  "dimensions": ["start_month"],
  "metrics": ["mrr", "active_subscriptions"],
  "filters": [
    {"dimension": "status", "operator": "=", "value": "active"}
  ]
}
```

### MRR by Plan

```json
{
  "dataset": "subscriptions",
  "dimensions": ["plan_tier"],
  "metrics": ["mrr", "active_subscriptions", "avg_mrr_per_account"]
}
```

### Churn Analysis

```json
{
  "dataset": "subscriptions",
  "dimensions": ["cancel_reason"],
  "metrics": ["churned_mrr"],
  "filters": [
    {"dimension": "cancel_date", "operator": ">=", "value": "2024-01-01"}
  ]
}
```

### Customer Cohorts

```json
{
  "dataset": "accounts",
  "dimensions": ["signup_month", "acquisition_source"],
  "metrics": ["account_count", "avg_ltv"]
}
```

## Calculated Metrics Examples

### Net Revenue Retention

```sql
-- In BI tool
(Starting MRR + Expansion - Contraction - Churn) / Starting MRR * 100
```

### Quick Ratio

```sql
-- Measures growth efficiency
(New MRR + Expansion MRR) / (Churned MRR + Contraction MRR)
```

## Files

```
saas-metrics/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   └── sample-data.sql
├── queries/
│   ├── mrr-analysis.json
│   ├── churn-analysis.json
│   └── cohort-analysis.json
└── dashboards/
    └── saas-metrics-dashboard.json
```

