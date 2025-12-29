# Jupyter Widget

Interactive dataset explorer for Jupyter notebooks.

## Installation

```bash
pip install setupranali[jupyter]

# Or with all extras
pip install setupranali[all]
```

Required dependencies:
- `ipywidgets`
- `pandas` (optional, for DataFrame export)

---

## Quick Start

```python
from setupranali.jupyter import explore

# Launch interactive explorer
explorer = explore("http://localhost:8080", "your-api-key")
```

This opens an interactive widget with:
- Dataset selector
- Dimension/metric multi-select
- Query execution
- Results display
- DataFrame export

---

## DatasetExplorer

Full-featured explorer widget:

```python
from setupranali.jupyter import DatasetExplorer

explorer = DatasetExplorer(
    url="http://localhost:8080",
    api_key="your-api-key"
)
explorer.show()
```

### Features

- **Dataset dropdown** - Select from available datasets
- **Dimensions select** - Multi-select dimensions to group by
- **Metrics select** - Multi-select metrics to aggregate
- **Limit input** - Control result size
- **Run Query** - Execute and display results
- **Export to DataFrame** - Save results to `df` variable

---

## QuickQuery

Programmatic interface for quick queries:

```python
from setupranali.jupyter import QuickQuery

qq = QuickQuery("http://localhost:8080", "your-api-key")

# Query and get DataFrame directly
df = qq.run(
    dataset="orders",
    dimensions=["city", "product"],
    metrics=["total_revenue"],
    filters=[{"field": "order_date", "operator": "gte", "value": "2024-01-01"}],
    limit=1000
)

# Display
df.head()
```

### SQL Queries

```python
df = qq.sql(
    "SELECT city, SUM(revenue) as total FROM orders GROUP BY city",
    dataset="orders"
)
```

---

## Using with Existing Client

Pass an existing client:

```python
from setupranali import SetuPranali
from setupranali.jupyter import DatasetExplorer

client = SetuPranali(url="http://localhost:8080", api_key="key")

explorer = DatasetExplorer(client=client)
explorer.show()
```

---

## Programmatic Access

The explorer also supports programmatic queries:

```python
from setupranali.jupyter import DatasetExplorer

explorer = DatasetExplorer(url="http://localhost:8080", api_key="key")

# Query without showing widget
result = explorer.query(
    dataset="orders",
    dimensions=["city"],
    metrics=["revenue"]
)

df = result.to_dataframe()
```

---

## Example Notebook

```python
# Cell 1: Setup
from setupranali.jupyter import explore, QuickQuery

# Cell 2: Interactive exploration
explorer = explore("http://localhost:8080", "your-api-key")

# Cell 3: After running query in widget, access the DataFrame
print(df.head())  # 'df' is auto-exported

# Cell 4: Quick programmatic query
qq = QuickQuery("http://localhost:8080", "your-api-key")
revenue_by_city = qq.run("orders", dimensions=["city"], metrics=["total_revenue"])

# Cell 5: Visualization
import matplotlib.pyplot as plt

revenue_by_city.plot(kind='bar', x='city', y='total_revenue')
plt.title('Revenue by City')
plt.show()
```

---

## Widget Screenshot

```
┌─────────────────────────────────────────────────┐
│ 🔍 SetuPranali Dataset Explorer                 │
├─────────────────────────────────────────────────┤
│ Dataset: [Orders (orders)        ▼]             │
├─────────────────────────────────────────────────┤
│ Dimensions:          │ Metrics:                 │
│ ┌─────────────────┐  │ ┌─────────────────┐      │
│ │ ☑ City (string) │  │ │ ☑ Revenue       │      │
│ │ ☐ Product       │  │ │ ☑ Order Count   │      │
│ │ ☐ Order Date    │  │ │ ☐ Avg Value     │      │
│ └─────────────────┘  │ └─────────────────┘      │
├─────────────────────────────────────────────────┤
│ Limit: [100  ]  [▶ Run Query] [📊 Export]       │
├─────────────────────────────────────────────────┤
│ ✅ Returned 10 rows                              │
│ ⏱️ Execution time: 45ms                          │
│ 💾 Cached: False                                 │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │   city      revenue    order_count          │ │
│ │   Mumbai    150000     245                  │ │
│ │   Delhi     120000     198                  │ │
│ │   ...       ...        ...                  │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Widget Not Displaying

```python
# Enable widget extension
!jupyter nbextension enable --py widgetsnbextension

# For JupyterLab
!jupyter labextension install @jupyter-widgets/jupyterlab-manager
```

### Import Error

```python
# Check if ipywidgets is installed
!pip install ipywidgets

# Restart kernel after installation
```

### Connection Issues

```python
# Test connection first
from setupranali import SetuPranali

client = SetuPranali(url="http://localhost:8080", api_key="key")
print(client.health())  # Should print status
```

---

## Next Steps

- [Python SDK](python.md)
- [Query API](../api-reference/query.md)
- [Examples](../examples/index.md)

