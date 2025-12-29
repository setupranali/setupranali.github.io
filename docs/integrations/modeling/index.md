# Modeling Layers

Integrate SetuPranali with existing semantic layers.

---

## Overview

Already have a modeling layer? SetuPranali works with:

- **dbt** - Reference dbt models as datasets
- **SQL Views** - Use existing database views
- **Other tools** - LookML, Cube, custom solutions

---

## Integration Approaches

<div class="grid cards" markdown>

-   :material-source-branch:{ .lg .middle } **dbt Integration**

    ---

    Point datasets to dbt mart tables.

    [:octicons-arrow-right-24: dbt Guide](dbt.md)

-   :material-view-grid:{ .lg .middle } **SQL Views**

    ---

    Use existing views as data sources.

    [:octicons-arrow-right-24: Views Guide](views.md)

</div>

---

## Why Use External Models?

### Existing Investment

Your team already has:
- Tested transformations
- Documented models
- CI/CD pipelines

SetuPranali adds:
- Security layer (API keys, RLS)
- BI connectivity (OData, WDC)
- Performance layer (caching, rate limiting)

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────┐
│  dbt / Views / Models                                   │
│  - Data transformation                                  │
│  - Business logic                                       │
│  - Testing                                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  SetuPranali                                 │
│  - Access control                                       │
│  - BI protocol translation                              │
│  - Caching & performance                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  BI Tools (Power BI, Tableau, etc.)                     │
│  - Visualization                                        │
│  - Dashboards                                           │
│  - Self-service                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Comparison

| Approach | Complexity | Flexibility |
|----------|------------|-------------|
| dbt models | Low | High (leverage dbt) |
| SQL views | Low | Medium |
| Custom SQL | Medium | High |
| Standalone | Low | Full control |

