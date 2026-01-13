# Web UI & Dashboard

SetuPranali includes a comprehensive web-based admin dashboard and modeling interface.

---

## Overview

The Web UI provides:

- **Dashboard** - System overview, metrics, and health monitoring
- **Datasets Management** - Browse, view, and manage semantic datasets
- **Data Sources** - Configure and test database connections
- **API Keys** - Create and manage authentication keys
- **Query Playground** - Interactive query builder and SQL testing
- **Contract Editor** - Visual YAML catalog editor with validation
- **Analytics** - Query patterns and performance insights
- **Modeling Studio** - Full-featured BI modeling interface
- **Settings** - System configuration

---

## Accessing the Web UI

### Development

```bash
cd webui
npm install
npm run dev
```

Open http://localhost:5173

### Production

The Web UI is included in the Docker image and served automatically when running:

```bash
docker run -p 8080:8080 -p 5173:5173 adeygifting/connector:latest
```

---

## Dashboard

**URL**: `/dashboard`

The dashboard provides:

- **System Health** - Server status, uptime, version
- **Query Metrics** - Total queries, success rate, average response time
- **Cache Statistics** - Hit rate, cache size
- **Recent Queries** - Last executed queries with execution times
- **Data Source Status** - Connection health for all sources
- **Quick Actions** - Links to common tasks

---

## Datasets

**URL**: `/datasets`

### Features

- **Browse Datasets** - List all configured datasets
- **View Details** - Click any dataset to see:
  - Dimensions and metrics
  - Source configuration
  - RLS settings
  - Sample queries
- **Test Queries** - Execute sample queries directly from the UI
- **Schema Preview** - View table structure and sample data

### Usage

1. Navigate to `/datasets`
2. Click on a dataset name
3. View dimensions, metrics, and configuration
4. Use sample queries to test the dataset

---

## Data Sources

**URL**: `/sources`

### Features

- **List Sources** - View all configured data sources
- **Add Source** - Create new database connections
- **Test Connection** - Verify connectivity before saving
- **Edit Source** - Update connection settings
- **Delete Source** - Remove unused connections
- **View Details** - See connection status and metadata

### Adding a Source

1. Click "Add Source"
2. Select database type (PostgreSQL, Snowflake, etc.)
3. Enter connection details:
   - Host/Account
   - Database
   - Credentials
   - SSL settings
4. Click "Test Connection"
5. Save if test succeeds

---

## API Keys

**URL**: `/api-keys`

### Features

- **List Keys** - View all API keys with metadata
- **Create Key** - Generate new API keys
- **Copy Key** - One-click copy to clipboard
- **View Details** - See tenant, role, usage stats
- **Revoke Key** - Disable keys instantly
- **Usage Tracking** - See last used timestamp

### Creating an API Key

1. Click "Create API Key"
2. Enter:
   - Name (for identification)
   - Tenant (for RLS)
   - Role (admin/viewer)
3. Click "Create"
4. **Important**: Copy the key immediately - it's only shown once!

---

## Query Playground

**URL**: `/playground`

### Features

- **Visual Query Builder** - Drag-and-drop interface
- **SQL Mode** - Direct SQL execution
- **Dataset Selection** - Choose from available datasets
- **Dimension/Metric Selection** - Build queries visually
- **Filter Builder** - Add WHERE conditions
- **Sort & Limit** - Configure result ordering
- **Execute & Preview** - Run queries and see results
- **SQL Preview** - See generated SQL before execution
- **Result Visualization** - Charts and tables

### Using Query Playground

1. Select a dataset
2. Add dimensions (for grouping)
3. Add metrics (for aggregations)
4. Add filters (optional)
5. Set sort order and limit
6. Click "Execute Query"
7. View results in table or chart format

---

## Contract Editor

**URL**: `/contracts`

### Features

- **YAML Editor** - Syntax-highlighted editor
- **Model Selection** - Choose semantic model to edit
- **Validation** - Real-time YAML validation
- **Auto-save** - Local storage for drafts
- **Export** - Download YAML contracts
- **Import** - Load existing contracts
- **Error Highlighting** - Visual feedback for syntax errors

### Using Contract Editor

1. Select a semantic model from dropdown
2. View/edit YAML content
3. Validation runs automatically
4. Save to local storage
5. Export when ready

---

## Analytics

**URL**: `/analytics`

### Features

- **Query Patterns** - Most common queries
- **Performance Metrics** - Response times, cache hit rates
- **Usage Statistics** - Queries per dataset, per tenant
- **Time-based Analysis** - Trends over time
- **Error Tracking** - Failed queries and reasons
- **Export Data** - Download analytics reports

---

## Settings

**URL**: `/settings`

### Configuration Options

- **API URL** - Backend API endpoint
- **Theme** - Light/dark mode
- **Cache Settings** - Enable/disable caching
- **Rate Limiting** - Configure limits
- **Notifications** - Alert preferences

---

## Modeling Studio

**URL**: `/modeling`

The Modeling Studio is a full-screen, professional BI modeling interface.

### Features

#### Schema Panel (Left)
- Browse database schemas
- View tables and columns
- Lazy loading for large schemas
- Search and filter
- Sample data preview

#### ERD Canvas (Center)
- Drag-and-drop table placement
- Visual relationship builder
- Join type configuration
- Cardinality indicators
- Zoom and pan controls

#### Semantic Model Panel (Right)
- Define dimensions
- Create measures
- Calculated fields
- Time intelligence
- Format strings

#### Query Workbench (Bottom)
- Semantic query builder
- SQL mode
- Result visualization
- Query explanation
- Expression validation

### Using Modeling Studio

1. **Connect Source**
   - Click "Add Source"
   - Configure connection
   - Test and save

2. **Build ERD**
   - Drag tables from schema panel
   - Connect tables with relationships
   - Configure join types

3. **Define Semantic Model**
   - Add dimensions from tables
   - Create measures with aggregations
   - Add calculated fields

4. **Query Data**
   - Use query workbench
   - Build semantic queries
   - Execute and visualize results

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Execute Query | `Ctrl/Cmd + Enter` |
| Save | `Ctrl/Cmd + S` |
| New Query | `Ctrl/Cmd + N` |
| Toggle SQL Mode | `Ctrl/Cmd + Shift + S` |

---

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

---

## Troubleshooting

### UI Not Loading

1. Check backend is running: `curl http://localhost:8080/v1/health`
2. Check frontend is running: `curl http://localhost:5173`
3. Check browser console for errors (F12)

### API Connection Errors

1. Verify `VITE_API_URL` is set correctly
2. Check CORS settings on backend
3. Verify API key is valid

### Query Execution Fails

1. Check API key has correct permissions
2. Verify dataset exists
3. Check backend logs for errors

---

## Next Steps

- [Modeling Studio Guide](modeling-ui.md)
- [Query Playground Tutorial](../getting-started/first-query.md)
- [API Reference](../api-reference/index.md)

