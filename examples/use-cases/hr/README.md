# HR Analytics Example

Human Resources analytics with SetuPranali.

## Overview

This example covers:
- Headcount tracking
- Attrition analysis
- Compensation analytics
- Recruitment funnel

## Key Metrics

| Metric | Description |
|--------|-------------|
| Headcount | Total employees |
| Attrition Rate | Employees leaving % |
| Time to Hire | Days to fill positions |
| Cost per Hire | Recruitment cost |
| Employee Satisfaction | Survey scores |
| Compensation Ratio | Salary vs market |

## Quick Start

```bash
docker-compose up -d
```

## Catalog Configuration

```yaml
sources:
  hr_db:
    type: postgres
    connection:
      host: ${DB_HOST}
      database: hr_analytics
      user: ${DB_USER}
      password: ${DB_PASSWORD}

datasets:
  employees:
    name: "Employees"
    description: "Employee master data"
    source: hr_db
    table: employees
    
    dimensions:
      - name: employee_id
        type: string
        sql: employee_id
        primary_key: true
        
      - name: department
        type: string
        sql: department
        
      - name: team
        type: string
        sql: team
        
      - name: job_title
        type: string
        sql: job_title
        
      - name: job_level
        type: string
        sql: job_level
        description: "IC1-IC5, M1-M3, D1-D3, VP, C-Level"
        
      - name: location
        type: string
        sql: location
        
      - name: country
        type: string
        sql: country
        
      - name: hire_date
        type: date
        sql: hire_date
        
      - name: hire_month
        type: string
        sql: TO_CHAR(hire_date, 'YYYY-MM')
        
      - name: tenure_years
        type: number
        sql: EXTRACT(YEAR FROM age(CURRENT_DATE, hire_date))
        
      - name: employment_type
        type: string
        sql: employment_type
        description: "full_time, part_time, contractor"
        
      - name: status
        type: string
        sql: status
        description: "active, terminated, on_leave"
        
      - name: termination_reason
        type: string
        sql: termination_reason
        
      - name: manager_id
        type: string
        sql: manager_id
        
      - name: is_manager
        type: boolean
        sql: is_manager
    
    metrics:
      - name: headcount
        type: count
        sql: employee_id
        
      - name: active_employees
        type: count
        sql: CASE WHEN status = 'active' THEN employee_id END
        
      - name: terminated_employees
        type: count
        sql: CASE WHEN status = 'terminated' THEN employee_id END
        
      - name: avg_tenure
        type: avg
        sql: EXTRACT(YEAR FROM age(CURRENT_DATE, hire_date))
        format: ".1f years"

  compensation:
    name: "Compensation"
    description: "Salary and compensation data"
    source: hr_db
    table: compensation
    
    dimensions:
      - name: employee_id
        type: string
        sql: employee_id
        
      - name: effective_date
        type: date
        sql: effective_date
        
      - name: pay_grade
        type: string
        sql: pay_grade
        
      - name: currency
        type: string
        sql: currency
    
    metrics:
      - name: base_salary
        type: sum
        sql: base_salary
        format: "$,.0f"
        
      - name: avg_salary
        type: avg
        sql: base_salary
        format: "$,.0f"
        
      - name: total_compensation
        type: sum
        sql: base_salary + bonus_target + equity_value
        format: "$,.0f"
        
      - name: median_salary
        type: custom
        sql: PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY base_salary)
        format: "$,.0f"

  recruitment:
    name: "Recruitment"
    description: "Job requisitions and candidates"
    source: hr_db
    table: recruitment
    
    dimensions:
      - name: requisition_id
        type: string
        sql: requisition_id
        
      - name: job_title
        type: string
        sql: job_title
        
      - name: department
        type: string
        sql: department
        
      - name: location
        type: string
        sql: location
        
      - name: status
        type: string
        sql: status
        description: "open, filled, cancelled"
        
      - name: opened_date
        type: date
        sql: opened_date
        
      - name: source
        type: string
        sql: source
        description: "referral, linkedin, job_board, agency"
        
      - name: stage
        type: string
        sql: current_stage
        description: "applied, screening, interview, offer, hired"
    
    metrics:
      - name: open_positions
        type: count
        sql: CASE WHEN status = 'open' THEN requisition_id END
        
      - name: applications
        type: count
        sql: requisition_id
        
      - name: time_to_hire
        type: avg
        sql: CASE WHEN status = 'filled' THEN filled_date - opened_date END
        format: ".0f days"
        
      - name: cost_per_hire
        type: avg
        sql: CASE WHEN status = 'filled' THEN recruitment_cost END
        format: "$,.0f"
        
      - name: offer_acceptance_rate
        type: custom
        sql: |
          COUNT(CASE WHEN status = 'filled' THEN 1 END)::float /
          NULLIF(COUNT(CASE WHEN current_stage IN ('offer', 'hired') THEN 1 END), 0) * 100
        format: ".1f%"

  surveys:
    name: "Employee Surveys"
    description: "Engagement and satisfaction surveys"
    source: hr_db
    table: surveys
    
    dimensions:
      - name: survey_date
        type: date
        sql: survey_date
        
      - name: survey_type
        type: string
        sql: survey_type
        description: "engagement, pulse, exit, onboarding"
        
      - name: department
        type: string
        sql: department
        
      - name: question_category
        type: string
        sql: question_category
    
    metrics:
      - name: response_count
        type: count
        sql: response_id
        
      - name: avg_score
        type: avg
        sql: score
        format: ".2f"
        
      - name: enps
        type: custom
        sql: |
          (COUNT(CASE WHEN score >= 9 THEN 1 END)::float -
           COUNT(CASE WHEN score <= 6 THEN 1 END)::float) /
          COUNT(*) * 100
        description: "Employee Net Promoter Score"
        format: ".0f"

# Sensitive HR data - restrict access
api_keys:
  hr_admin_key:
    name: "HR Admin"
    tenant_id: "hr_full"
    
  hr_manager_key:
    name: "HR Managers"
    tenant_id: "hr_limited"
    
  exec_key:
    name: "Executives"
    tenant_id: "exec_summary"

# Row-level security by department for managers
rls:
  employees:
    field: department
    operator: "="
```

## Sample Queries

### Headcount by Department

```json
{
  "dataset": "employees",
  "dimensions": ["department"],
  "metrics": ["active_employees", "avg_tenure"],
  "filters": [
    {"dimension": "status", "operator": "=", "value": "active"}
  ]
}
```

### Monthly Attrition

```json
{
  "dataset": "employees",
  "dimensions": ["hire_month"],
  "metrics": ["headcount", "terminated_employees"],
  "filters": [
    {"dimension": "hire_date", "operator": ">=", "value": "2023-01-01"}
  ]
}
```

### Compensation by Level

```json
{
  "dataset": "compensation",
  "dimensions": ["pay_grade"],
  "metrics": ["avg_salary", "median_salary"],
  "orderBy": [{"field": "pay_grade", "direction": "asc"}]
}
```

### Recruitment Funnel

```json
{
  "dataset": "recruitment",
  "dimensions": ["stage"],
  "metrics": ["applications"],
  "filters": [
    {"dimension": "opened_date", "operator": ">=", "value": "2024-01-01"}
  ]
}
```

### Engagement Trends

```json
{
  "dataset": "surveys",
  "dimensions": ["survey_date", "department"],
  "metrics": ["avg_score", "enps"],
  "filters": [
    {"dimension": "survey_type", "operator": "=", "value": "engagement"}
  ]
}
```

## Privacy Considerations

1. **Anonymize individual data** - Only show aggregates
2. **Minimum group size** - Don't show groups < 5 employees
3. **Hide salary details** - Show ranges, not exact values
4. **Audit access** - Log all queries to sensitive data

## Files

```
hr/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   └── sample-data.sql
├── queries/
│   ├── headcount.json
│   ├── attrition.json
│   └── compensation.json
└── dashboards/
    └── hr-dashboard.json
```

