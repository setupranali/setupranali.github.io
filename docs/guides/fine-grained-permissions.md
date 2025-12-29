# Fine-Grained Permissions

Implement column-level and dataset-level access control for enterprise security.

---

## Overview

SetuPranali provides comprehensive access control:

- **Dataset-Level Access**: Control who can access which datasets
- **Column-Level Access**: Restrict dimensions and metrics per user/role
- **Row-Level Security (RLS)**: Automatic tenant isolation
- **Role-Based Access Control (RBAC)**: Define roles with permissions
- **Policy-Based Access Control**: Flexible policy rules
- **Data Masking**: Mask sensitive column values
- **Query Limits**: Restrict result sizes and time ranges

---

## Quick Start

### 1. Define Roles in catalog.yaml

```yaml
# catalog.yaml
permissions:
  enabled: true
  default_effect: deny  # deny-by-default
  
  roles:
    - name: analyst
      datasets:
        - dataset: "*"
          actions: [query, read]
    
    - name: viewer
      datasets:
        - dataset: "public_*"
          actions: [read]
          max_rows: 1000
    
    - name: admin
      datasets:
        - dataset: "*"
          actions: [query, read, write, admin]
      can_create_api_keys: true
      can_manage_sources: true
  
  api_key_roles:
    "sk_live_analyst123": [analyst]
    "sk_live_admin456": [admin]
```

### 2. Query with Permissions

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: sk_live_analyst123" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

---

## Dataset-Level Access Control

### Allow Access to Specific Datasets

```yaml
roles:
  - name: sales_analyst
    datasets:
      - dataset: orders
        actions: [query, read]
      
      - dataset: customers
        actions: [query, read]
      
      - dataset: products
        actions: [read]  # Read-only, no queries
```

### Wildcard Patterns

```yaml
roles:
  - name: finance_team
    datasets:
      # All finance datasets
      - dataset: "finance_*"
        actions: [query, read]
      
      # All datasets in reporting schema
      - dataset: "reporting.*"
        actions: [read]
```

### Deny Access

```yaml
roles:
  - name: restricted_user
    datasets:
      # Allow most datasets
      - dataset: "*"
        actions: [query]
      
      # Deny sensitive datasets
      - dataset: hr_salaries
        effect: deny
      
      - dataset: "pii_*"
        effect: deny
```

---

## Column-Level Access Control

### Dimension/Metric Whitelisting

Only allow specific columns:

```yaml
roles:
  - name: limited_analyst
    datasets:
      - dataset: orders
        actions: [query]
        
        # Only these dimensions allowed
        allowed_dimensions:
          - order_date
          - region
          - product_category
        
        # Only these metrics allowed
        allowed_metrics:
          - order_count
          - total_amount
```

### Dimension/Metric Blacklisting

Deny specific columns:

```yaml
roles:
  - name: external_partner
    datasets:
      - dataset: orders
        actions: [query]
        
        # These dimensions are hidden
        denied_dimensions:
          - customer_email
          - customer_phone
          - internal_notes
        
        # These metrics are hidden
        denied_metrics:
          - profit_margin
          - cost_price
```

### Per-Column Permissions

```yaml
roles:
  - name: support_agent
    datasets:
      - dataset: customers
        actions: [query, read]
        
        columns:
          - name: email
            effect: allow
            mask: EMAIL  # Show a***@domain.com
          
          - name: phone
            effect: allow
            mask: PARTIAL  # Show 5***9
          
          - name: ssn
            effect: deny  # Completely hidden
          
          - name: address
            effect: allow
            mask: "***"  # Replace with ***
```

---

## Data Masking

### Masking Types

| Mask | Example Input | Output |
|------|---------------|--------|
| `***` | `john@email.com` | `***` |
| `HASH` | `john@email.com` | `a3f2b8c1` |
| `PARTIAL` | `1234567890` | `1********0` |
| `EMAIL` | `john@email.com` | `j***@email.com` |

### Configure Masking

```yaml
roles:
  - name: customer_service
    datasets:
      - dataset: customers
        columns:
          - name: credit_card
            mask: PARTIAL
          
          - name: ssn
            mask: "XXX-XX-****"
          
          - name: email
            mask: EMAIL
          
          - name: salary
            mask: HASH
```

### Custom Masking Functions

```yaml
columns:
  - name: phone
    mask_function: mask_phone  # Custom function
```

Implement in Python:

```python
def mask_phone(value: str) -> str:
    """Custom phone masking."""
    if len(value) >= 10:
        return f"({value[:3]}) ***-{value[-4:]}"
    return "***"
```

---

## Row-Level Security (RLS)

### Tenant Isolation

Automatically filter rows by tenant:

```yaml
roles:
  - name: tenant_user
    datasets:
      - dataset: "*"
        actions: [query]
        rls_field: tenant_id  # Column containing tenant ID
```

The user's tenant ID (from API key, OAuth, or SAML) is used to filter:

```sql
-- Automatically added to queries
WHERE tenant_id = 'user_tenant_id'
```

### Custom RLS Filters

```yaml
roles:
  - name: regional_manager
    datasets:
      - dataset: orders
        actions: [query]
        rls_filter: "region IN ('US-East', 'US-West')"
      
      - dataset: employees
        actions: [query]
        rls_filter: "department = 'Sales' AND active = true"
```

### Dynamic RLS with Attributes

```yaml
roles:
  - name: department_head
    datasets:
      - dataset: employees
        actions: [query]
        # Uses department from OAuth/SAML attributes
        rls_filter: "department = '${user.department}'"
```

---

## Query Limits

### Row Limits

```yaml
roles:
  - name: free_tier
    datasets:
      - dataset: "*"
        actions: [query]
        max_rows: 1000  # Max 1000 rows per query
```

### Time Range Limits

```yaml
roles:
  - name: trial_user
    datasets:
      - dataset: "*"
        actions: [query]
        allowed_time_range: 30  # Only last 30 days
```

### Dimension/Metric Limits

```yaml
roles:
  - name: simple_queries
    datasets:
      - dataset: "*"
        actions: [query]
        max_dimensions: 3  # Max 3 dimensions per query
        max_metrics: 5     # Max 5 metrics per query
```

---

## Role-Based Access Control (RBAC)

### Define Roles

```yaml
roles:
  # Base role with minimal access
  - name: base_user
    datasets:
      - dataset: "public_*"
        actions: [read]
  
  # Analyst inherits base_user
  - name: analyst
    inherits: [base_user]
    datasets:
      - dataset: "*"
        actions: [query, read]
  
  # Senior analyst with export
  - name: senior_analyst
    inherits: [analyst]
    datasets:
      - dataset: "*"
        actions: [query, read, export]
  
  # Admin with everything
  - name: admin
    inherits: [senior_analyst]
    datasets:
      - dataset: "*"
        actions: [query, read, write, admin]
    can_create_api_keys: true
    can_manage_sources: true
    can_view_audit_logs: true
```

### Assign Roles

```yaml
# By API Key
api_key_roles:
  "sk_live_analyst123": [analyst]
  "sk_live_senior456": [senior_analyst]
  "sk_live_admin789": [admin]

# By User ID (OAuth/SAML)
user_roles:
  "user@company.com": [analyst]
  "admin@company.com": [admin]

# By Tenant
tenant_roles:
  "tenant_123": [base_user]
  "tenant_456": [analyst]
```

### Role Priority

Higher priority roles are evaluated first:

```yaml
roles:
  - name: admin
    priority: 100  # Highest
  
  - name: analyst
    priority: 50
  
  - name: viewer
    priority: 10  # Lowest
```

---

## Policy-Based Access Control

### Define Policies

```yaml
policies:
  # Allow analysts during business hours
  - id: business_hours_only
    name: Business Hours Access
    principals: [analyst]
    resources: ["*"]
    actions: [query]
    effect: allow
    conditions:
      time_range:
        start: 9
        end: 18
  
  # Deny access from unknown IPs
  - id: ip_whitelist
    name: IP Whitelist
    principals: ["*"]
    resources: ["*"]
    actions: ["*"]
    effect: deny
    conditions:
      ip_range: ["10.0.0.0/8", "192.168.0.0/16"]
```

### Policy Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `ip_range` | Allowed IP ranges | `["10.0.0.0/8"]` |
| `time_range` | Allowed hours (UTC) | `{start: 9, end: 18}` |
| `tenant_id` | Specific tenant | `"tenant_123"` |
| `attributes` | User attributes | `{department: "Sales"}` |

### Policy Precedence

1. **Explicit Deny** - Always wins
2. **Explicit Allow** - If no deny
3. **Default Effect** - If no match (deny by default)

---

## API Key Scoping

### Create Scoped API Keys

```yaml
api_keys:
  - key: "sk_live_readonly"
    roles: [viewer]
    datasets: ["orders", "products"]
    expires_at: "2025-12-31"
  
  - key: "sk_live_analytics"
    roles: [analyst]
    tenant_id: "tenant_123"
    
  - key: "sk_live_admin"
    roles: [admin]
```

### API Key Restrictions

```yaml
api_keys:
  - key: "sk_partner_xyz"
    roles: [partner]
    
    # IP restrictions
    allowed_ips: ["203.0.113.0/24"]
    
    # Rate limits
    rate_limit: 100  # requests per minute
    
    # Expiration
    expires_at: "2025-06-30T23:59:59Z"
```

---

## Audit Logging

### Enable Audit Logs

```yaml
permissions:
  audit_enabled: true
```

### Audit Log Format

```json
{
  "timestamp": "2025-12-29T10:30:00Z",
  "event": "permission_check",
  "principal": {
    "api_key": "sk_live_***",
    "user_id": "user@company.com",
    "tenant_id": "tenant_123",
    "roles": ["analyst"]
  },
  "resource": {
    "type": "dataset",
    "id": "orders"
  },
  "action": "query",
  "result": {
    "allowed": true,
    "matched_roles": ["analyst"],
    "applied_filters": ["tenant_id = 'tenant_123'"]
  }
}
```

---

## Helm Configuration

```yaml
# values.yaml
permissions:
  enabled: true
  defaultEffect: deny
  
  roles:
    - name: analyst
      datasets:
        - dataset: "*"
          actions: [query, read]
    
    - name: admin
      datasets:
        - dataset: "*"
          actions: [query, read, write, admin]
      canCreateApiKeys: true
      canManageSources: true
  
  apiKeyRoles:
    # From secret
    existingSecret: api-key-roles
  
  auditEnabled: true
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PERMISSIONS_ENABLED` | Enable fine-grained permissions | `true` |
| `PERMISSIONS_DEFAULT_EFFECT` | Default permission effect | `deny` |
| `PERMISSIONS_AUDIT_ENABLED` | Enable audit logging | `true` |
| `PERMISSIONS_CACHE_TTL` | Permission cache TTL (seconds) | `300` |
| `ADMIN_API_KEY` | Admin API key (auto-creates admin role) | - |

---

## Examples

### Multi-Tenant SaaS

```yaml
permissions:
  enabled: true
  default_effect: deny
  
  roles:
    # Each tenant gets isolated access
    - name: tenant_user
      datasets:
        - dataset: "*"
          actions: [query, read]
          rls_field: tenant_id
          max_rows: 50000
    
    # Super admin can see all
    - name: super_admin
      datasets:
        - dataset: "*"
          actions: [query, read, write, admin]
      can_manage_sources: true
  
  tenant_roles:
    "*": [tenant_user]  # All tenants get tenant_user role
  
  api_key_roles:
    "sk_super_admin": [super_admin]
```

### Data Privacy Compliance

```yaml
permissions:
  enabled: true
  
  roles:
    - name: gdpr_compliant
      datasets:
        - dataset: customers
          actions: [query]
          
          # Hide PII columns
          denied_dimensions:
            - email
            - phone
            - address
            - date_of_birth
          
          # Mask remaining PII
          columns:
            - name: name
              mask: PARTIAL
            - name: customer_id
              mask: HASH
```

### Department-Based Access

```yaml
permissions:
  enabled: true
  
  roles:
    - name: sales
      datasets:
        - dataset: orders
          actions: [query]
          rls_filter: "department = 'Sales'"
        - dataset: customers
          actions: [query]
    
    - name: finance
      datasets:
        - dataset: orders
          actions: [query]
        - dataset: revenue
          actions: [query]
        - dataset: costs
          actions: [query]
    
    - name: hr
      datasets:
        - dataset: employees
          actions: [query]
          denied_dimensions: [salary, ssn]
  
  user_roles:
    "alice@company.com": [sales]
    "bob@company.com": [finance]
    "carol@company.com": [hr]
```

---

## Best Practices

1. **Deny by Default**: Always use `default_effect: deny`
2. **Least Privilege**: Grant minimum required permissions
3. **Use Roles**: Don't assign permissions directly to users
4. **Role Inheritance**: Create hierarchy for maintainability
5. **Audit Everything**: Enable audit logging
6. **Review Regularly**: Audit permissions periodically
7. **Test Permissions**: Verify with test API keys

---

## Troubleshooting

### Access Denied

```json
{
  "error": "Access denied",
  "code": "ERR_4003",
  "details": {
    "dataset": "orders",
    "reason": "No matching permission found",
    "principal": "sk_live_***"
  }
}
```

**Solutions:**
1. Check API key has correct roles assigned
2. Verify role has dataset permission
3. Check for explicit deny policies
4. Review role priority

### Column Not Available

```json
{
  "error": "Dimension not available",
  "code": "ERR_3004",
  "details": {
    "dimension": "customer_email",
    "reason": "Column denied by permission"
  }
}
```

**Solutions:**
1. Check `denied_dimensions` in role
2. Verify `allowed_dimensions` whitelist
3. Check column-level permissions

### Missing RLS Filter

```json
{
  "warning": "No RLS filter applied",
  "details": {
    "dataset": "orders",
    "tenant_id": null
  }
}
```

**Solutions:**
1. Verify tenant_id is provided
2. Check `rls_field` configuration
3. Verify API key has tenant association

