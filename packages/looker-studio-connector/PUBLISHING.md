# Looker Studio Connector - Publishing Guide

This document details the process for publishing the SetuPranali connector to the Google Looker Studio connector gallery.

---

## Connector Overview

### Connector ID

```
setupranali-connector
```

### Display Name

```
SetuPranali Semantic Layer
```

### Description

```
Connect Looker Studio to SetuPranali semantic layer for governed metrics and dimensions. 
Query pre-defined metrics with automatic Row-Level Security, caching, and multi-tenant support.
```

### Icon

Located at: `packages/looker-studio-connector/assets/icon.png`

Requirements:
- 96x96 pixels
- PNG format
- Transparent background

### Category

```
Analytics, Business Intelligence, Data Warehouse
```

---

## Manifest Configuration

### appsscript.json

```json
{
  "timeZone": "UTC",
  "dependencies": {},
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "dataStudio": {
    "name": "SetuPranali Semantic Layer",
    "company": "SetuPranali Community",
    "companyUrl": "https://setupranali.github.io",
    "logoUrl": "https://setupranali.github.io/assets/logo.svg",
    "addonUrl": "https://setupranali.github.io/integrations/bi-tools/looker-studio/",
    "supportUrl": "https://github.com/setupranali/setupranali.github.io/issues",
    "description": "Connect to SetuPranali semantic layer for governed metrics and dimensions with automatic Row-Level Security.",
    "sources": ["setupranali"],
    "templates": {
      "default": "1abc123def456"
    }
  }
}
```

---

## Publishing Steps

### 1. Prepare the Connector

1. **Test locally** using Apps Script editor
2. **Verify all functions** work correctly:
   - `getAuthType()`
   - `getConfig()`
   - `getSchema()`
   - `getData()`

### 2. Create Apps Script Project

1. Go to [script.google.com](https://script.google.com)
2. Create new project
3. Copy connector code from `apps-script/Code.gs`
4. Update `appsscript.json` manifest

### 3. Deploy as Connector

1. In Apps Script: **Deploy** > **New deployment**
2. Select type: **Add-on** > **Looker Studio Community Connector**
3. Fill in details:
   - Description
   - Icon URL
   - Terms of Service URL
   - Privacy Policy URL

### 4. Submit for Review

1. Go to [Google Marketplace SDK](https://console.cloud.google.com/apis/library/appsmarket-component.googleapis.com)
2. Enable the API
3. Configure OAuth consent screen
4. Submit connector for review

### 5. Review Checklist

Google reviews connectors for:

- [ ] **Functionality**: All required functions implemented
- [ ] **Performance**: Reasonable response times
- [ ] **Security**: Proper authentication handling
- [ ] **Privacy**: No unauthorized data access
- [ ] **Branding**: Accurate company information
- [ ] **Documentation**: Help links and descriptions

---

## Required Functions

### getAuthType()

```javascript
function getAuthType() {
  return cc.newAuthTypeResponse()
    .setAuthType(cc.AuthType.KEY)
    .setHelpUrl('https://setupranali.github.io/guides/api-keys/')
    .build();
}
```

### getConfig()

```javascript
function getConfig(request) {
  var config = cc.getConfig();
  
  config.newTextInput()
    .setId('serverUrl')
    .setName('Server URL')
    .setHelpText('SetuPranali server URL (e.g., https://your-server.com)')
    .setPlaceholder('https://your-server.com');
  
  config.newSelectSingle()
    .setId('dataset')
    .setName('Dataset')
    .setHelpText('Select dataset to query')
    .setIsDynamic(true);
  
  config.setDateRangeRequired(true);
  
  return config.build();
}
```

### getSchema()

```javascript
function getSchema(request) {
  return getSchemaForDataset(request.configParams.dataset);
}
```

### getData()

```javascript
function getData(request) {
  return fetchDataFromSetuPranali(request);
}
```

---

## Template Report

Create a sample report template:

1. Create Looker Studio report using the connector
2. Design example visualizations:
   - Time series chart
   - Bar chart by dimension
   - Scorecard with metrics
   - Table with details
3. Save as template
4. Get template ID for manifest

---

## Branding Assets

### Logo

- **Size**: 128x128 pixels minimum
- **Format**: SVG preferred, PNG accepted
- **Background**: Transparent

### Screenshots

Required screenshots:
1. Configuration screen
2. Data source fields
3. Sample report

---

## Support Resources

### Help Center Article

Create documentation at:
```
https://setupranali.github.io/integrations/bi-tools/looker-studio/
```

Contents:
- Getting started guide
- Configuration options
- Troubleshooting
- FAQs

### Support Channels

- GitHub Issues: Primary support channel
- Email: community@setupranali.io
- Discord: Community chat

---

## Monitoring

### Usage Metrics

Track connector usage via:
- Apps Script execution logs
- SetuPranali API analytics
- Google Cloud Console

### Error Monitoring

Enable Stackdriver logging in manifest:
```json
{
  "exceptionLogging": "STACKDRIVER"
}
```

---

## Maintenance

### Version Updates

1. Update connector code
2. Test thoroughly
3. Create new deployment
4. Update manifest version
5. Notify users of changes

### Deprecation

If deprecating connector:
1. Announce 90 days in advance
2. Provide migration guide
3. Update connector to show warning
4. Remove from gallery after period

---

## Legal Requirements

### Terms of Service

Link to: `https://setupranali.github.io/terms/`

### Privacy Policy

Link to: `https://setupranali.github.io/privacy/`

### Data Handling

- Connector only accesses data user authorizes
- No data is stored by connector
- All requests go through SetuPranali server
- Credentials stored securely in Google

