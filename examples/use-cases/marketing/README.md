# Marketing Analytics Example

Track marketing campaigns, conversions, and attribution with SetuPranali.

## Overview

This example includes:
- Campaign performance tracking
- Multi-touch attribution
- Conversion funnel analysis
- ROI calculations

## Key Metrics

| Metric | Description |
|--------|-------------|
| Impressions | Ad views |
| Clicks | Ad clicks |
| CTR | Click-through rate |
| Conversions | Completed goals |
| CPA | Cost per acquisition |
| ROAS | Return on ad spend |

## Quick Start

```bash
docker-compose up -d
```

## Catalog Configuration

```yaml
sources:
  marketing_db:
    type: postgres
    connection:
      host: ${DB_HOST}
      database: marketing
      user: ${DB_USER}
      password: ${DB_PASSWORD}

datasets:
  campaigns:
    name: "Campaigns"
    description: "Marketing campaign performance"
    source: marketing_db
    table: campaign_stats
    
    dimensions:
      - name: date
        type: date
        sql: date
        
      - name: campaign_id
        type: string
        sql: campaign_id
        
      - name: campaign_name
        type: string
        sql: campaign_name
        
      - name: channel
        type: string
        sql: channel
        description: "google, facebook, linkedin, email, etc."
        
      - name: ad_group
        type: string
        sql: ad_group
        
      - name: creative
        type: string
        sql: creative_name
        
      - name: audience
        type: string
        sql: audience_name
        
      - name: country
        type: string
        sql: country
        
      - name: device
        type: string
        sql: device_type
    
    metrics:
      - name: impressions
        type: sum
        sql: impressions
        
      - name: clicks
        type: sum
        sql: clicks
        
      - name: ctr
        type: custom
        sql: SUM(clicks)::float / NULLIF(SUM(impressions), 0) * 100
        description: "Click-through rate %"
        format: ".2f%"
        
      - name: spend
        type: sum
        sql: spend
        format: "$,.2f"
        
      - name: conversions
        type: sum
        sql: conversions
        
      - name: revenue
        type: sum
        sql: revenue
        format: "$,.2f"
        
      - name: cpc
        type: custom
        sql: SUM(spend) / NULLIF(SUM(clicks), 0)
        description: "Cost per click"
        format: "$,.2f"
        
      - name: cpa
        type: custom
        sql: SUM(spend) / NULLIF(SUM(conversions), 0)
        description: "Cost per acquisition"
        format: "$,.2f"
        
      - name: roas
        type: custom
        sql: SUM(revenue) / NULLIF(SUM(spend), 0)
        description: "Return on ad spend"
        format: ".2f"

  conversions:
    name: "Conversions"
    description: "Conversion events with attribution"
    source: marketing_db
    table: conversions
    
    dimensions:
      - name: conversion_date
        type: date
        sql: converted_at::date
        
      - name: conversion_type
        type: string
        sql: conversion_type
        description: "signup, purchase, lead, etc."
        
      - name: first_touch_channel
        type: string
        sql: first_touch_channel
        
      - name: last_touch_channel
        type: string
        sql: last_touch_channel
        
      - name: first_touch_campaign
        type: string
        sql: first_touch_campaign
        
      - name: last_touch_campaign
        type: string
        sql: last_touch_campaign
        
      - name: attribution_model
        type: string
        sql: attribution_model
        description: "first_touch, last_touch, linear, time_decay"
    
    metrics:
      - name: conversion_count
        type: count
        sql: conversion_id
        
      - name: conversion_value
        type: sum
        sql: value
        format: "$,.2f"
        
      - name: avg_conversion_value
        type: avg
        sql: value
        format: "$,.2f"

  funnel_events:
    name: "Funnel Events"
    description: "User journey through conversion funnel"
    source: marketing_db
    table: funnel_events
    
    dimensions:
      - name: event_date
        type: date
        sql: event_date
        
      - name: funnel_stage
        type: string
        sql: stage
        description: "awareness, interest, consideration, intent, purchase"
        
      - name: channel
        type: string
        sql: source_channel
        
      - name: campaign
        type: string
        sql: campaign_name
    
    metrics:
      - name: users
        type: count_distinct
        sql: user_id
        
      - name: events
        type: count
        sql: event_id

  email_campaigns:
    name: "Email Campaigns"
    description: "Email marketing performance"
    source: marketing_db
    table: email_stats
    
    dimensions:
      - name: send_date
        type: date
        sql: sent_at::date
        
      - name: campaign_name
        type: string
        sql: campaign_name
        
      - name: email_type
        type: string
        sql: email_type
        description: "newsletter, promotional, transactional"
        
      - name: segment
        type: string
        sql: audience_segment
    
    metrics:
      - name: sent
        type: sum
        sql: emails_sent
        
      - name: delivered
        type: sum
        sql: emails_delivered
        
      - name: opened
        type: sum
        sql: emails_opened
        
      - name: clicked
        type: sum
        sql: emails_clicked
        
      - name: open_rate
        type: custom
        sql: SUM(emails_opened)::float / NULLIF(SUM(emails_delivered), 0) * 100
        format: ".2f%"
        
      - name: click_rate
        type: custom
        sql: SUM(emails_clicked)::float / NULLIF(SUM(emails_opened), 0) * 100
        format: ".2f%"
        
      - name: unsubscribes
        type: sum
        sql: unsubscribes
```

## Sample Queries

### Channel Performance

```json
{
  "dataset": "campaigns",
  "dimensions": ["channel"],
  "metrics": ["spend", "conversions", "revenue", "roas", "cpa"],
  "filters": [
    {"dimension": "date", "operator": ">=", "value": "2024-01-01"}
  ],
  "orderBy": [{"field": "revenue", "direction": "desc"}]
}
```

### Campaign ROI

```json
{
  "dataset": "campaigns",
  "dimensions": ["campaign_name", "channel"],
  "metrics": ["spend", "revenue", "roas"],
  "filters": [
    {"dimension": "spend", "operator": ">", "value": "100"}
  ],
  "orderBy": [{"field": "roas", "direction": "desc"}]
}
```

### Funnel Analysis

```json
{
  "dataset": "funnel_events",
  "dimensions": ["funnel_stage"],
  "metrics": ["users"],
  "orderBy": [{"field": "funnel_stage", "direction": "asc"}]
}
```

### Attribution Comparison

```json
{
  "dataset": "conversions",
  "dimensions": ["first_touch_channel", "last_touch_channel"],
  "metrics": ["conversion_count", "conversion_value"]
}
```

## Files

```
marketing/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   └── sample-data.sql
├── queries/
│   ├── channel-performance.json
│   ├── attribution.json
│   └── funnel-analysis.json
└── dashboards/
    └── marketing-dashboard.json
```

