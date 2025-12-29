# @setupranali/looker-studio

Looker Studio (Google Data Studio) connector for SetuPranali semantic layer.

## Features

- 📊 **Native Looker Studio Integration** - Community connector for seamless data access
- 🔐 **API Key Authentication** - Secure connection with your SetuPranali server
- 📈 **Automatic Schema Discovery** - Dimensions and metrics auto-detected
- 📅 **Date Range Support** - Native Looker Studio date filtering
- 🚀 **Easy Deployment** - Deploy to Google Apps Script in minutes

## Installation

### Option 1: Use Pre-deployed Connector

1. Open Looker Studio
2. Click **Create** > **Data Source**
3. Search for "SetuPranali" in Community Connectors
4. Enter your server URL and API key
5. Select a dataset and connect

### Option 2: Deploy Your Own

```bash
# Install the package
npm install @setupranali/looker-studio

# Or clone and deploy manually
git clone https://github.com/setupranali/setupranali.github.io.git
cd packages/looker-studio-connector

# Install dependencies
npm install

# Deploy to Google Apps Script
npm run deploy
```

## Usage

### As a Looker Studio Connector

1. **Create Data Source**
   - Go to Looker Studio > Create > Data Source
   - Select "SetuPranali" connector
   
2. **Configure Connection**
   - Server URL: `https://your-server.com`
   - Dataset: `orders` (or your dataset name)
   - Row Limit: `10000` (optional)
   
3. **Authenticate**
   - Enter your SetuPranali API key
   
4. **Create Reports**
   - Use the data source in your reports
   - All dimensions and metrics are automatically available

### As a TypeScript Library

```typescript
import { SetuPranaliConnector } from '@setupranali/looker-studio';

// Create connector instance
const connector = new SetuPranaliConnector({
  url: 'https://your-server.com',
  apiKey: 'your-api-key'
});

// Test connection
const isConnected = await connector.testConnection();
console.log('Connected:', isConnected);

// Get available datasets
const datasets = await connector.getDatasets();
console.log('Datasets:', datasets);

// Get schema for a dataset
const schema = await connector.getSchema('orders');
console.log('Schema:', schema);

// Query data
const data = await connector.getData({
  dataset: 'orders',
  dimensions: ['region', 'product_category'],
  metrics: ['revenue', 'order_count'],
  limit: 1000
});
console.log('Data:', data);
```

## Configuration

### Connector Settings

| Setting | Description | Required |
|---------|-------------|----------|
| Server URL | SetuPranali server URL | ✅ |
| Dataset | Dataset ID to query | ✅ |
| Row Limit | Max rows to fetch (default: 10000) | |

### Environment Variables

For deployment:

```bash
# Google Apps Script project ID
CLASP_PROJECT_ID=your-project-id
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/setupranali/setupranali.github.io.git
cd packages/looker-studio-connector

# Install dependencies
npm install

# Build
npm run build

# Watch mode
npm run dev
```

### Deploy to Apps Script

```bash
# Login to Google
npx clasp login

# Create new Apps Script project
npx clasp create --type standalone --title "SetuPranali Connector"

# Push code
npm run deploy
```

### Test Locally

```bash
npm test
```

## API Reference

### SetuPranaliConnector

```typescript
class SetuPranaliConnector {
  constructor(config: ConnectorConfig);
  
  // Test connection
  testConnection(): Promise<boolean>;
  
  // Get datasets
  getDatasets(): Promise<DatasetInfo[]>;
  
  // Get dataset info
  getDatasetInfo(datasetId: string): Promise<DatasetInfo>;
  
  // Get Looker Studio schema
  getSchema(datasetId: string): Promise<SchemaField[]>;
  
  // Query data
  getData(request: QueryRequest): Promise<QueryResponse>;
  
  // Execute SQL
  executeSql(sql: string, dataset: string): Promise<QueryResponse>;
  
  // Format for Looker Studio
  formatForLookerStudio(response: QueryResponse, schema: SchemaField[]): any[][];
}
```

### Helper Functions

```typescript
// Create a schema field
createSchemaField(name: string, options?: Partial<SchemaField>): SchemaField;

// Create a dimension
createDimension(name: string, dataType?: DataType, options?: Partial<SchemaField>): SchemaField;

// Create a metric
createMetric(name: string, options?: Partial<SchemaField>): SchemaField;
```

## Troubleshooting

### Connection Failed

1. Verify SetuPranali server is accessible
2. Check API key is valid
3. Ensure CORS is configured for Google domains

### No Data Returned

1. Verify dataset exists
2. Check dimensions and metrics are valid
3. Review date range filters

### Schema Not Loading

1. Clear connector cache in Looker Studio
2. Re-authorize the connector
3. Check server logs for errors

## Security

- API keys are stored securely in Google's User Properties
- All requests use HTTPS
- Row-Level Security is enforced by SetuPranali

## Resources

- [Looker Studio Documentation](https://developers.google.com/looker-studio)
- [SetuPranali Documentation](https://setupranali.github.io)
- [Community Connector Guide](https://developers.google.com/looker-studio/connector)

## License

Apache 2.0 - See [LICENSE](../../LICENSE)

