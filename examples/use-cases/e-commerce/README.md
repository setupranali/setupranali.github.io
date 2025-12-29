# E-Commerce Analytics Example

A complete example for e-commerce analytics with SetuPranali.

## Overview

This example includes:
- Orders, customers, products datasets
- Revenue, conversion, inventory metrics
- Multi-tenant support for marketplaces
- Ready-to-use BI tool configurations

## Business Metrics

| Metric | Description |
|--------|-------------|
| Revenue | Total sales revenue |
| Orders | Number of orders |
| AOV | Average Order Value |
| Conversion Rate | Orders / Sessions |
| Customer LTV | Lifetime Value |
| Repeat Rate | Returning customers % |

## Quick Start

```bash
docker-compose up -d
```

## Data Model

```
┌─────────────┐     ┌─────────────┐
│  Customers  │────<│   Orders    │
└─────────────┘     └──────┬──────┘
                          │
                    ┌─────┴─────┐
                    │Order Items│
                    └─────┬─────┘
                          │
                   ┌──────┴──────┐
                   │  Products   │
                   └─────────────┘
```

## Catalog Configuration

```yaml
sources:
  ecommerce_db:
    type: postgres
    connection:
      host: ${DB_HOST}
      database: ecommerce
      user: ${DB_USER}
      password: ${DB_PASSWORD}

datasets:
  orders:
    name: "Orders"
    description: "E-commerce order transactions"
    source: ecommerce_db
    table: orders
    
    dimensions:
      - name: order_id
        type: string
        sql: order_id
        primary_key: true
        
      - name: order_date
        type: date
        sql: order_date
        
      - name: order_month
        type: string
        sql: TO_CHAR(order_date, 'YYYY-MM')
        
      - name: customer_id
        type: string
        sql: customer_id
        
      - name: status
        type: string
        sql: status
        
      - name: channel
        type: string
        sql: channel
        description: "Sales channel (web, mobile, store)"
        
      - name: payment_method
        type: string
        sql: payment_method
        
      - name: shipping_method
        type: string
        sql: shipping_method
        
      - name: region
        type: string
        sql: shipping_region
        
      - name: country
        type: string
        sql: shipping_country
        
      - name: promo_code
        type: string
        sql: promo_code
    
    metrics:
      - name: revenue
        type: sum
        sql: subtotal
        description: "Gross revenue before discounts"
        format: "$,.2f"
        
      - name: net_revenue
        type: sum
        sql: subtotal - discount_amount
        description: "Revenue after discounts"
        format: "$,.2f"
        
      - name: order_count
        type: count
        sql: order_id
        
      - name: aov
        type: custom
        sql: SUM(subtotal) / NULLIF(COUNT(order_id), 0)
        description: "Average Order Value"
        format: "$,.2f"
        
      - name: unique_customers
        type: count_distinct
        sql: customer_id
        
      - name: items_sold
        type: sum
        sql: item_count
        
      - name: discount_amount
        type: sum
        sql: discount_amount
        format: "$,.2f"
        
      - name: shipping_revenue
        type: sum
        sql: shipping_amount
        format: "$,.2f"

  customers:
    name: "Customers"
    description: "Customer profiles and lifetime metrics"
    source: ecommerce_db
    table: customers
    
    dimensions:
      - name: customer_id
        type: string
        sql: customer_id
        primary_key: true
        
      - name: first_order_date
        type: date
        sql: first_order_date
        
      - name: acquisition_channel
        type: string
        sql: acquisition_channel
        
      - name: segment
        type: string
        sql: customer_segment
        
      - name: country
        type: string
        sql: country
        
      - name: is_subscriber
        type: boolean
        sql: email_subscribed
    
    metrics:
      - name: customer_count
        type: count
        sql: customer_id
        
      - name: total_ltv
        type: sum
        sql: lifetime_value
        format: "$,.2f"
        
      - name: avg_ltv
        type: avg
        sql: lifetime_value
        format: "$,.2f"
        
      - name: total_orders
        type: sum
        sql: order_count
        
      - name: avg_orders
        type: avg
        sql: order_count

  products:
    name: "Products"
    description: "Product catalog and inventory"
    source: ecommerce_db
    table: products
    
    dimensions:
      - name: product_id
        type: string
        sql: product_id
        primary_key: true
        
      - name: product_name
        type: string
        sql: name
        
      - name: category
        type: string
        sql: category
        
      - name: subcategory
        type: string
        sql: subcategory
        
      - name: brand
        type: string
        sql: brand
        
      - name: supplier
        type: string
        sql: supplier
    
    metrics:
      - name: product_count
        type: count
        sql: product_id
        
      - name: avg_price
        type: avg
        sql: price
        format: "$,.2f"
        
      - name: total_inventory
        type: sum
        sql: stock_quantity
        
      - name: inventory_value
        type: sum
        sql: stock_quantity * cost
        format: "$,.2f"

# Row-Level Security for multi-tenant marketplace
rls:
  orders:
    field: seller_id
    operator: "="
```

## Sample Queries

### Daily Revenue

```json
{
  "dataset": "orders",
  "dimensions": ["order_date"],
  "metrics": ["revenue", "order_count", "aov"],
  "filters": [
    {"dimension": "status", "operator": "!=", "value": "cancelled"}
  ],
  "orderBy": [{"field": "order_date", "direction": "asc"}]
}
```

### Revenue by Channel

```json
{
  "dataset": "orders",
  "dimensions": ["channel"],
  "metrics": ["revenue", "order_count", "unique_customers"],
  "filters": [
    {"dimension": "order_date", "operator": ">=", "value": "2024-01-01"}
  ]
}
```

### Top Products

```json
{
  "dataset": "order_items",
  "dimensions": ["product_name", "category"],
  "metrics": ["revenue", "units_sold"],
  "orderBy": [{"field": "revenue", "direction": "desc"}],
  "limit": 20
}
```

### Customer Cohort Analysis

```json
{
  "dataset": "customers",
  "dimensions": ["acquisition_channel", "segment"],
  "metrics": ["customer_count", "avg_ltv", "avg_orders"]
}
```

## BI Tool Dashboards

### Power BI

Import `powerbi/ecommerce-dashboard.pbit` for a ready-to-use dashboard.

### Tableau

Use `tableau/ecommerce-workbook.twb` for pre-built visualizations.

### Metabase

Import questions from `metabase/questions.json`.

## Files

```
e-commerce/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   └── sample-data.sql
├── queries/
│   ├── daily-revenue.json
│   ├── channel-analysis.json
│   └── product-performance.json
└── bi-tools/
    ├── powerbi/
    ├── tableau/
    └── metabase/
```

