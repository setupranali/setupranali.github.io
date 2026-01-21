# BI Modeling UI

SetuPranali includes a powerful web-based BI modeling interface similar to Power BI / Looker / Metabase.

## Overview

The Modeling Studio provides:
- **Source Connection UI** - Add, edit, test, and manage database connections
- **Schema Discovery Panel** - Browse schemas, tables, and columns with lazy loading
- **ERD Builder** - Drag-and-drop canvas for building entity relationships
- **Semantic Model** - Define dimensions, measures, and calculated fields
- **Query Workbench** - Execute semantic and SQL queries with visualization

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Modeling Studio UI                          │
├─────────────┬─────────────────────────────┬─────────────────────────┤
│   Schema    │        ERD Canvas           │    Semantic Model       │
│   Panel     │    (React Flow)             │       Panel            │
│             │                             │                         │
│  - Schemas  │  ┌─────┐    ┌─────┐        │  - Dimensions           │
│  - Tables   │  │Table│────│Table│        │  - Measures             │
│  - Columns  │  └─────┘    └─────┘        │  - Calculated Fields    │
│             │       │          │         │  - Time Intelligence    │
│             │  ┌─────┐    ┌─────┐        │                         │
│             │  │Table│────│Table│        │                         │
│             │  └─────┘    └─────┘        │                         │
├─────────────┴─────────────────────────────┴─────────────────────────┤
│                        Query Workbench                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ [ Semantic Mode ]  [ SQL Mode ]           [ ▶ Run Query ]     │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │ Results  │  Chart  │  Generated SQL                           │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Backend Architecture

### Module Structure

```
app/modeling/
├── __init__.py                 # Module exports
├── schema_introspection.py     # Database schema discovery
├── erd_manager.py              # ERD persistence (nodes, edges)
├── semantic_model.py           # Dimensions, measures, calculated fields
├── query_planner.py            # SQL generation from semantic queries
└── routes.py                   # REST API endpoints
```

### Key Classes

#### SchemaIntrospector
Discovers database metadata across different engines:
- `get_schemas()` - List schemas/databases
- `get_tables(schema)` - List tables in schema
- `get_columns(schema, table)` - Get column metadata
- `get_sample_data(schema, table)` - Preview data

#### ERDManager
Manages entity-relationship diagrams:
- **TableNode** - Table on canvas (position, columns, collapsed state)
- **RelationshipEdge** - Join between tables (cardinality, join type)
- **ERDModel** - Complete graph with nodes and edges

#### SemanticModelManager
Manages semantic layer definitions:
- **Dimension** - Categorical columns for grouping
- **Measure** - Aggregated metrics (SUM, COUNT, AVG, etc.)
- **CalculatedField** - Derived expressions
- **TimeIntelligence** - YTD, MoM, YoY calculations

#### QueryPlanner
Generates SQL from semantic queries:
- Resolves dimensions and measures to columns
- Builds JOIN paths using ERD relationships
- Applies filters and sorts
- Validates expressions

## Frontend Architecture

### Component Structure

```
webui/src/
├── components/
│   └── modeling/
│       ├── SourceConnectionDialog.tsx  # Connection config modal
│       ├── SchemaPanel.tsx             # Tree view for schemas
│       ├── ERDCanvas.tsx               # React Flow canvas
│       ├── SemanticModelPanel.tsx      # Dimensions & measures
│       └── QueryWorkbench.tsx          # SQL/semantic query UI
├── pages/
│   └── ModelingStudio.tsx              # Main page layout
├── store/
│   └── modeling.ts                     # Zustand state management
├── lib/
│   └── modeling-api.ts                 # API client
└── types/
    └── modeling.ts                     # TypeScript types
```

### State Management

Uses Zustand for global state:
- **Sources** - Data source connections
- **Schema Tree** - Expanded/collapsed state, search
- **ERD Canvas** - Zoom, pan, selection
- **Semantic Model** - Selected dimensions/measures
- **Query Workbench** - Mode, SQL text, results

### Key Libraries

| Library | Purpose |
|---------|---------|
| @xyflow/react | ERD canvas (drag, connect, pan, zoom) |
| @monaco-editor/react | SQL editor with syntax highlighting |
| recharts | Result visualization (bar, line charts) |
| react-resizable-panels | Resizable layout panels |
| @tanstack/react-query | Data fetching & caching |
| zustand | State management |

## API Reference

### Schema Introspection

```http
# List schemas
GET /v1/modeling/sources/{sourceId}/schemas

# List tables in schema
GET /v1/modeling/sources/{sourceId}/schemas/{schema}/tables

# Get columns for table
GET /v1/modeling/sources/{sourceId}/schemas/{schema}/tables/{table}/columns

# Get sample data
GET /v1/modeling/sources/{sourceId}/schemas/{schema}/tables/{table}/sample?limit=100
```

### ERD Management

```http
# CRUD for ERD models
POST   /v1/modeling/erd
GET    /v1/modeling/erd
GET    /v1/modeling/erd/{modelId}
PUT    /v1/modeling/erd/{modelId}
DELETE /v1/modeling/erd/{modelId}

# Node operations
POST   /v1/modeling/erd/{modelId}/nodes
DELETE /v1/modeling/erd/{modelId}/nodes/{nodeId}

# Edge operations
POST   /v1/modeling/erd/{modelId}/edges
DELETE /v1/modeling/erd/{modelId}/edges/{edgeId}
```

### Semantic Model Management

```http
# CRUD for semantic models
POST   /v1/modeling/semantic
GET    /v1/modeling/semantic
GET    /v1/modeling/semantic/{modelId}
PUT    /v1/modeling/semantic/{modelId}
DELETE /v1/modeling/semantic/{modelId}

# Dimension operations
POST   /v1/modeling/semantic/{modelId}/dimensions
DELETE /v1/modeling/semantic/{modelId}/dimensions/{dimId}

# Measure operations
POST   /v1/modeling/semantic/{modelId}/measures
DELETE /v1/modeling/semantic/{modelId}/measures/{measureId}

# Calculated field operations
POST   /v1/modeling/semantic/{modelId}/calculated
```

### Query Workbench

```http
# Execute semantic query
POST /v1/modeling/query/semantic
{
  "erdModelId": "...",
  "semanticModelId": "...",
  "query": {
    "dimensions": ["Region", "Product"],
    "measures": ["Total Revenue", "Order Count"],
    "filters": [],
    "sorts": [{"field": "Total Revenue", "direction": "DESC"}],
    "limit": 100
  }
}

# Execute raw SQL
POST /v1/modeling/query/sql
{
  "sql": "SELECT * FROM orders LIMIT 10",
  "sourceId": "..."
}

# Explain query (without executing)
POST /v1/modeling/query/explain

# Validate expression
POST /v1/modeling/query/validate-expression
{
  "expression": "[Revenue] / [Orders]"
}
```

## Database Schema

### ERD Models (SQLite)

```sql
CREATE TABLE erd_models (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_id TEXT NOT NULL,
    description TEXT,
    data TEXT NOT NULL,          -- JSON: nodes, edges
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_erd_source_id ON erd_models(source_id);
```

### Semantic Models (SQLite)

```sql
CREATE TABLE semantic_models (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_id TEXT NOT NULL,
    erd_model_id TEXT,
    description TEXT,
    data TEXT NOT NULL,          -- JSON: dimensions, measures, etc.
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_semantic_source_id ON semantic_models(source_id);
```

## Usage Example

### 1. Create Connection

```typescript
const result = await modelingApi.testConnection({
  engine: 'postgres',
  host: 'localhost',
  port: 5432,
  database: 'sales',
  username: 'admin',
  password: 'secret',
  ssl: true
});
```

### 2. Build ERD

```typescript
// Create ERD model
const erd = await modelingApi.createERDModel({
  name: 'Sales Data Model',
  sourceId: 'pg-sales'
});

// Add tables
await modelingApi.addTableNode(erd.id, {
  schemaName: 'public',
  tableName: 'orders',
  position: { x: 100, y: 100 }
});

// Create relationship
await modelingApi.addRelationship(erd.id, {
  sourceNodeId: 'orders-node',
  sourceColumn: 'customer_id',
  targetNodeId: 'customers-node',
  targetColumn: 'id',
  cardinality: 'N:1',
  joinType: 'left'
});
```

### 3. Define Semantic Model

```typescript
const semantic = await modelingApi.createSemanticModel({
  name: 'Sales Metrics',
  sourceId: 'pg-sales',
  erdModelId: erd.id
});

// Add dimension
await modelingApi.addDimension(semantic.id, {
  name: 'Product Category',
  sourceColumn: 'category',
  sourceTable: 'public.products',
  dimensionType: 'categorical'
});

// Add measure
await modelingApi.addMeasure(semantic.id, {
  name: 'Total Revenue',
  expression: 'revenue',
  aggregation: 'SUM',
  sourceTable: 'public.orders',
  formatString: '$#,##0.00'
});
```

### 4. Run Semantic Query

```typescript
const result = await modelingApi.executeSemanticQuery(
  erd.id,
  semantic.id,
  {
    dimensions: ['Product Category'],
    measures: ['Total Revenue'],
    sorts: [{ field: 'Total Revenue', direction: 'DESC' }],
    limit: 10
  }
);

console.log(result.rows);
// [
//   { "Product Category": "Electronics", "Total Revenue": 150000 },
//   { "Product Category": "Clothing", "Total Revenue": 89000 },
//   ...
// ]
```

## Best Practices

### ERD Design
- Start with fact tables (orders, transactions)
- Add dimension tables and create relationships
- Use descriptive relationship names
- Mark inactive relationships for alternative join paths

### Semantic Model
- Use business-friendly names (not column names)
- Add descriptions for self-documentation
- Create calculated metrics for complex KPIs
- Configure time intelligence for date dimensions

### Performance
- Use lazy loading for large schemas
- Cache introspection results
- Limit sample data queries
- Use LIMIT in semantic queries

## YAML Contract Export/Import

The Modeling Studio integrates with the Contract Editor for seamless YAML management:

### Export

```http
GET /v1/modeling/semantic/{modelId}/yaml
```

Returns the semantic model in YAML format with:
- All dimensions and metrics
- **sourceTable** for each dimension and measure
- Proper field extraction (removes aggregation wrappers)
- Calculated fields and time intelligence

### Import

```http
PUT /v1/modeling/semantic/{modelId}/from-yaml
Content-Type: application/json
{
  "content": "..."
}
```

Updates the semantic model from YAML, preserving:
- Individual `sourceTable` assignments
- Field mappings
- Calculated expressions

### Contract Editor Integration

1. **Pull from Model** - Generates YAML with correct `sourceTable` mappings
2. **Push to Model** - Updates semantic model from edited YAML
3. **Validation** - Pre-query validation ensures all `sourceTable` values exist in ERD
4. **Error Messages** - Clear guidance when columns are mapped to wrong tables

### Key Features

- **Automatic sourceTable Inclusion** - All fields include `sourceTable` in YAML
- **Table Validation** - Validates `sourceTable` exists in ERD before query execution
- **Bulk Operations** - Export/import all contracts at once
- **Error Recovery** - Helpful error messages guide users to fix table mappings

## Roadmap

- [ ] Visual join validation (type compatibility)
- [ ] Drag dimension from schema to semantic panel
- [ ] Auto-detect relationships from foreign keys
- [ ] Export semantic model to dbt/Cube.js
- [ ] Collaborative editing (websocket sync)
- [ ] Version history for models
- [x] YAML contract export (✅ Available)

