# Financial Analytics Example

Financial reporting and analysis with SetuPranali.

## Overview

This example covers:
- Revenue & expense tracking
- P&L statements
- Budget vs actuals
- Cash flow analysis

## Key Metrics

| Metric | Description |
|--------|-------------|
| Revenue | Total income |
| Expenses | Total costs |
| Gross Profit | Revenue - COGS |
| Net Income | Revenue - All Expenses |
| EBITDA | Earnings before interest, taxes, depreciation |
| Burn Rate | Monthly cash spend |

## Quick Start

```bash
docker-compose up -d
```

## Catalog Configuration

```yaml
sources:
  finance_db:
    type: postgres
    connection:
      host: ${DB_HOST}
      database: finance
      user: ${DB_USER}
      password: ${DB_PASSWORD}

datasets:
  transactions:
    name: "Financial Transactions"
    description: "All financial transactions"
    source: finance_db
    table: transactions
    
    dimensions:
      - name: transaction_date
        type: date
        sql: transaction_date
        
      - name: fiscal_month
        type: string
        sql: TO_CHAR(transaction_date, 'YYYY-MM')
        
      - name: fiscal_quarter
        type: string
        sql: |
          CONCAT('FY', EXTRACT(YEAR FROM transaction_date), '-Q', 
                 CEIL(EXTRACT(MONTH FROM transaction_date)/3.0)::int)
        
      - name: fiscal_year
        type: number
        sql: EXTRACT(YEAR FROM transaction_date)
        
      - name: account_type
        type: string
        sql: account_type
        description: "revenue, expense, asset, liability"
        
      - name: account_category
        type: string
        sql: account_category
        
      - name: account_name
        type: string
        sql: account_name
        
      - name: department
        type: string
        sql: department
        
      - name: cost_center
        type: string
        sql: cost_center
        
      - name: project
        type: string
        sql: project_code
        
      - name: vendor
        type: string
        sql: vendor_name
    
    metrics:
      - name: amount
        type: sum
        sql: amount
        format: "$,.2f"
        
      - name: revenue
        type: sum
        sql: CASE WHEN account_type = 'revenue' THEN amount ELSE 0 END
        format: "$,.2f"
        
      - name: expenses
        type: sum
        sql: CASE WHEN account_type = 'expense' THEN amount ELSE 0 END
        format: "$,.2f"
        
      - name: net_income
        type: custom
        sql: |
          SUM(CASE WHEN account_type = 'revenue' THEN amount ELSE 0 END) -
          SUM(CASE WHEN account_type = 'expense' THEN amount ELSE 0 END)
        format: "$,.2f"
        
      - name: transaction_count
        type: count
        sql: transaction_id

  budget:
    name: "Budget"
    description: "Annual budget by account"
    source: finance_db
    table: budget
    
    dimensions:
      - name: fiscal_year
        type: number
        sql: fiscal_year
        
      - name: fiscal_month
        type: string
        sql: fiscal_month
        
      - name: account_category
        type: string
        sql: account_category
        
      - name: department
        type: string
        sql: department
    
    metrics:
      - name: budget_amount
        type: sum
        sql: budget_amount
        format: "$,.2f"

  invoices:
    name: "Invoices"
    description: "Accounts receivable"
    source: finance_db
    table: invoices
    
    dimensions:
      - name: invoice_date
        type: date
        sql: invoice_date
        
      - name: due_date
        type: date
        sql: due_date
        
      - name: customer
        type: string
        sql: customer_name
        
      - name: status
        type: string
        sql: status
        description: "draft, sent, paid, overdue"
        
      - name: aging_bucket
        type: string
        sql: |
          CASE 
            WHEN status = 'paid' THEN 'Paid'
            WHEN CURRENT_DATE <= due_date THEN 'Current'
            WHEN CURRENT_DATE - due_date <= 30 THEN '1-30 Days'
            WHEN CURRENT_DATE - due_date <= 60 THEN '31-60 Days'
            WHEN CURRENT_DATE - due_date <= 90 THEN '61-90 Days'
            ELSE '90+ Days'
          END
    
    metrics:
      - name: invoice_count
        type: count
        sql: invoice_id
        
      - name: invoice_amount
        type: sum
        sql: amount
        format: "$,.2f"
        
      - name: outstanding_amount
        type: sum
        sql: CASE WHEN status != 'paid' THEN amount ELSE 0 END
        format: "$,.2f"
        
      - name: paid_amount
        type: sum
        sql: CASE WHEN status = 'paid' THEN amount ELSE 0 END
        format: "$,.2f"

  cash_flow:
    name: "Cash Flow"
    description: "Cash flow statement data"
    source: finance_db
    table: cash_flow
    
    dimensions:
      - name: date
        type: date
        sql: transaction_date
        
      - name: month
        type: string
        sql: TO_CHAR(transaction_date, 'YYYY-MM')
        
      - name: flow_type
        type: string
        sql: flow_type
        description: "operating, investing, financing"
        
      - name: category
        type: string
        sql: category
    
    metrics:
      - name: inflow
        type: sum
        sql: CASE WHEN amount > 0 THEN amount ELSE 0 END
        format: "$,.2f"
        
      - name: outflow
        type: sum
        sql: CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END
        format: "$,.2f"
        
      - name: net_cash_flow
        type: sum
        sql: amount
        format: "$,.2f"
```

## Sample Queries

### Monthly P&L

```json
{
  "dataset": "transactions",
  "dimensions": ["fiscal_month"],
  "metrics": ["revenue", "expenses", "net_income"],
  "orderBy": [{"field": "fiscal_month", "direction": "asc"}]
}
```

### Department Expenses

```json
{
  "dataset": "transactions",
  "dimensions": ["department", "account_category"],
  "metrics": ["expenses"],
  "filters": [
    {"dimension": "account_type", "operator": "=", "value": "expense"}
  ]
}
```

### Accounts Receivable Aging

```json
{
  "dataset": "invoices",
  "dimensions": ["aging_bucket"],
  "metrics": ["invoice_count", "outstanding_amount"]
}
```

### Cash Flow Statement

```json
{
  "dataset": "cash_flow",
  "dimensions": ["month", "flow_type"],
  "metrics": ["inflow", "outflow", "net_cash_flow"]
}
```

## Security Considerations

```yaml
# Restrict access to financial data
api_keys:
  finance_team_key:
    name: "Finance Team"
    tenant_id: "finance"
    
  exec_key:
    name: "Executives"
    tenant_id: "executive"

# Column-level restrictions
permissions:
  transactions:
    default_columns: [fiscal_month, account_category, amount]
    restricted_columns: [vendor, project]  # Only for finance_team
```

## Files

```
financial/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   └── sample-data.sql
├── queries/
│   ├── monthly-pl.json
│   └── cash-flow.json
└── reports/
    └── financial-dashboard.json
```

