# Looker Studio Integration

Connect Google Looker Studio (formerly Data Studio) to SetuPranali using a Community Connector.

## Overview

SetuPranali provides a Community Connector for Looker Studio that:

- Exposes your semantic layer datasets
- Applies row-level security automatically
- Supports all Looker Studio chart types
- Works with blending and calculated fields

---

## Quick Setup

### Step 1: Deploy the Connector

1. Open [Google Apps Script](https://script.google.com)
2. Create a new project: **"SetuPranali Connector"**
3. Copy the connector code below

### Step 2: Connector Code

Create these files in your Apps Script project:

#### `Code.gs`

```javascript
/**
 * SetuPranali Community Connector for Looker Studio
 */

var API_BASE_URL = 'https://your-setupranali-instance.com';

function getConfig(request) {
  var config = cc.getConfig();
  
  config.newTextInput()
    .setId('apiKey')
    .setName('API Key')
    .setHelpText('Your SetuPranali API key')
    .setPlaceholder('sk_...');
  
  config.newTextInput()
    .setId('serverUrl')
    .setName('Server URL')
    .setHelpText('SetuPranali server URL')
    .setPlaceholder('https://setupranali.your-domain.com');
  
  config.newSelectSingle()
    .setId('dataset')
    .setName('Dataset')
    .setHelpText('Select the dataset to connect');
  
  config.setDateRangeRequired(true);
  
  return config.build();
}

function getSchema(request) {
  var apiKey = request.configParams.apiKey;
  var serverUrl = request.configParams.serverUrl || API_BASE_URL;
  var dataset = request.configParams.dataset;
  
  // Fetch schema from SetuPranali
  var response = UrlFetchApp.fetch(serverUrl + '/v1/datasets/' + dataset, {
    headers: {
      'X-API-Key': apiKey
    }
  });
  
  var datasetInfo = JSON.parse(response.getContentText());
  var fields = [];
  
  // Map dimensions
  datasetInfo.dimensions.forEach(function(dim) {
    fields.push({
      name: dim.name,
      label: dim.label || dim.name,
      dataType: mapDataType(dim.type),
      semantics: {
        conceptType: 'DIMENSION'
      }
    });
  });
  
  // Map measures
  datasetInfo.measures.forEach(function(measure) {
    fields.push({
      name: measure.name,
      label: measure.label || measure.name,
      dataType: 'NUMBER',
      semantics: {
        conceptType: 'METRIC',
        isReaggregatable: true
      }
    });
  });
  
  return { schema: fields };
}

function getData(request) {
  var apiKey = request.configParams.apiKey;
  var serverUrl = request.configParams.serverUrl || API_BASE_URL;
  var dataset = request.configParams.dataset;
  
  var requestedFields = request.fields.map(function(field) {
    return field.name;
  });
  
  // Build query
  var queryPayload = {
    dataset: dataset,
    dimensions: [],
    measures: [],
    limit: 10000
  };
  
  // Separate dimensions and measures
  requestedFields.forEach(function(field) {
    // Check if it's a measure (you might want to track this differently)
    if (field.startsWith('sum_') || field.startsWith('count_') || field.startsWith('avg_')) {
      queryPayload.measures.push(field);
    } else {
      queryPayload.dimensions.push(field);
    }
  });
  
  // Add date range filter if provided
  if (request.dateRange) {
    queryPayload.filters = [{
      field: 'date',
      operator: 'between',
      value: [request.dateRange.startDate, request.dateRange.endDate]
    }];
  }
  
  // Fetch data from SetuPranali
  var response = UrlFetchApp.fetch(serverUrl + '/v1/query', {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify(queryPayload)
  });
  
  var result = JSON.parse(response.getContentText());
  
  // Transform to Looker Studio format
  var rows = result.data.map(function(row) {
    return {
      values: requestedFields.map(function(field) {
        return row[field];
      })
    };
  });
  
  return {
    schema: request.fields,
    rows: rows
  };
}

function mapDataType(type) {
  var typeMap = {
    'string': 'STRING',
    'number': 'NUMBER',
    'integer': 'NUMBER',
    'date': 'YEAR_MONTH_DAY',
    'datetime': 'YEAR_MONTH_DAY_SECOND',
    'timestamp': 'YEAR_MONTH_DAY_SECOND',
    'boolean': 'BOOLEAN'
  };
  return typeMap[type.toLowerCase()] || 'STRING';
}

function getAuthType() {
  return cc.newAuthTypeResponse()
    .setAuthType(cc.AuthType.NONE)
    .build();
}

function isAdminUser() {
  return false;
}

var cc = DataStudioApp.createCommunityConnector();
```

#### `appsscript.json`

```json
{
  "timeZone": "UTC",
  "dependencies": {},
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "dataStudio": {
    "name": "SetuPranali Connector",
    "company": "SetuPranali",
    "logoUrl": "https://setupranali.github.io/assets/logo.svg",
    "addonUrl": "https://setupranali.github.io",
    "supportUrl": "https://github.com/setupranali/setupranali.github.io/issues",
    "description": "Connect to your data warehouse through SetuPranali's semantic layer"
  }
}
```

### Step 3: Deploy the Connector

1. Click **Deploy → New deployment**
2. Select **Add-on → Looker Studio Community Connector**
3. Fill in details and click **Deploy**
4. Copy the **Deployment ID**

### Step 4: Use in Looker Studio

1. Go to [Looker Studio](https://lookerstudio.google.com)
2. Create new report → **Add data**
3. Search for your connector or use the deployment URL:
   ```
   https://lookerstudio.google.com/datasources/create?connectorId=YOUR_DEPLOYMENT_ID
   ```
4. Enter your SetuPranali API key and server URL
5. Select your dataset
6. Click **Connect**

---

## Features

### Automatic Row-Level Security

Your API key determines what data users can see:

```javascript
// API Key: tenant_id = "acme-corp"
// Users only see Acme Corp's data in all reports
```

### Date Range Filters

The connector automatically applies Looker Studio date range filters to your queries.

### Blending Support

Blend multiple SetuPranali datasets in a single report:

1. Add multiple data sources (different datasets)
2. Use Looker Studio's blend feature
3. Join on common dimensions

---

## Configuration Options

| Parameter | Description | Required |
|-----------|-------------|----------|
| `apiKey` | Your SetuPranali API key | Yes |
| `serverUrl` | SetuPranali server URL | Yes |
| `dataset` | Dataset to connect | Yes |

---

## Troubleshooting

### "Script error"

Check your Apps Script logs:
1. Open Apps Script project
2. View → Executions
3. Check for error details

### "Unauthorized"

Verify your API key:
```bash
curl -H "X-API-Key: your-key" https://your-server/v1/datasets
```

### "No data returned"

Check if your tenant has access to the data:
```bash
curl -X POST https://your-server/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "limit": 10}'
```

---

## Next Steps

- [Configure Datasets](../../guides/datasets.md)
- [Set Up Row-Level Security](../../guides/rls.md)
- [API Reference](../../api-reference/query.md)

