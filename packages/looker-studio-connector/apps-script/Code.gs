/**
 * SetuPranali Connector for Looker Studio
 * 
 * This Google Apps Script provides a community connector
 * for Looker Studio (Google Data Studio) to connect to SetuPranali.
 * 
 * @see https://setupranali.github.io/integrations/bi-tools/looker-studio/
 */

/**
 * Returns the authentication method required by the connector.
 * @return {object} AuthConfig
 */
function getAuthType() {
  return {
    type: 'KEY'
  };
}

/**
 * Returns the user configurable options for the connector.
 * @param {object} request - Config request parameters
 * @return {object} Config
 */
function getConfig(request) {
  var config = cc.getConfig();

  config
    .newInfo()
    .setId('instructions')
    .setText('Enter your SetuPranali server URL and select a dataset to visualize.');

  config
    .newTextInput()
    .setId('serverUrl')
    .setName('Server URL')
    .setHelpText('SetuPranali server URL (e.g., https://your-server.com)')
    .setPlaceholder('https://your-server.com')
    .setAllowOverride(true);

  config
    .newTextInput()
    .setId('dataset')
    .setName('Dataset')
    .setHelpText('Dataset ID to query (e.g., orders)')
    .setPlaceholder('orders')
    .setAllowOverride(true);

  config
    .newTextInput()
    .setId('limit')
    .setName('Row Limit')
    .setHelpText('Maximum number of rows to fetch (default: 10000)')
    .setPlaceholder('10000')
    .setAllowOverride(true);

  config.setDateRangeRequired(true);

  return config.build();
}

/**
 * Returns the schema for the given request.
 * @param {object} request - Schema request parameters
 * @return {object} Schema
 */
function getSchema(request) {
  var configParams = request.configParams;
  var serverUrl = configParams.serverUrl;
  var dataset = configParams.dataset;
  var apiKey = getApiKey();

  // Fetch dataset info from SetuPranali
  var datasetInfo = fetchDatasetInfo(serverUrl, dataset, apiKey);
  
  // Convert to Looker Studio schema
  var fields = [];
  
  // Add dimensions
  if (datasetInfo.dimensions) {
    datasetInfo.dimensions.forEach(function(dim) {
      fields.push({
        name: dim.name,
        label: formatLabel(dim.name),
        dataType: mapDataType(dim.type),
        semantics: {
          conceptType: 'DIMENSION'
        },
        description: dim.description || ''
      });
    });
  }
  
  // Add metrics
  if (datasetInfo.metrics) {
    datasetInfo.metrics.forEach(function(metric) {
      fields.push({
        name: metric.name,
        label: formatLabel(metric.name),
        dataType: 'NUMBER',
        semantics: {
          conceptType: 'METRIC',
          isReaggregatable: true
        },
        description: metric.description || ''
      });
    });
  }

  return { schema: fields };
}

/**
 * Returns the tabular data for the given request.
 * @param {object} request - Data request parameters
 * @return {object} Data
 */
function getData(request) {
  var configParams = request.configParams;
  var serverUrl = configParams.serverUrl;
  var dataset = configParams.dataset;
  var limit = parseInt(configParams.limit) || 10000;
  var apiKey = getApiKey();

  // Get requested fields
  var requestedFields = request.fields.map(function(field) {
    return field.name;
  });

  // Separate dimensions and metrics
  var datasetInfo = fetchDatasetInfo(serverUrl, dataset, apiKey);
  var dimensionNames = (datasetInfo.dimensions || []).map(function(d) { return d.name; });
  var metricNames = (datasetInfo.metrics || []).map(function(m) { return m.name; });

  var dimensions = requestedFields.filter(function(f) {
    return dimensionNames.indexOf(f) !== -1;
  });

  var metrics = requestedFields.filter(function(f) {
    return metricNames.indexOf(f) !== -1;
  });

  // Build filters from date range
  var filters = [];
  if (request.dateRange) {
    // Find date dimension
    var dateDim = datasetInfo.dimensions.find(function(d) {
      return d.type === 'date' || d.type === 'timestamp' || d.type === 'datetime';
    });
    
    if (dateDim) {
      filters.push({
        dimension: dateDim.name,
        operator: 'gte',
        value: request.dateRange.startDate
      });
      filters.push({
        dimension: dateDim.name,
        operator: 'lte',
        value: request.dateRange.endDate
      });
    }
  }

  // Query SetuPranali
  var queryResult = executeQuery(serverUrl, dataset, dimensions, metrics, filters, limit, apiKey);

  // Format response
  var schema = request.fields.map(function(field) {
    var dim = datasetInfo.dimensions.find(function(d) { return d.name === field.name; });
    var met = datasetInfo.metrics.find(function(m) { return m.name === field.name; });
    
    return {
      name: field.name,
      dataType: dim ? mapDataType(dim.type) : 'NUMBER'
    };
  });

  var rows = queryResult.rows.map(function(row) {
    return {
      values: requestedFields.map(function(fieldName) {
        var value = row[fieldName];
        return value !== null && value !== undefined ? value : '';
      })
    };
  });

  return {
    schema: schema,
    rows: rows
  };
}

/**
 * Validates the credentials provided by the user.
 * @return {boolean} True if credentials are valid
 */
function isAuthValid() {
  var apiKey = getApiKey();
  return apiKey !== null && apiKey.length > 0;
}

/**
 * Sets the credentials.
 * @param {object} request - Set credentials request
 * @return {object} Error object
 */
function setCredentials(request) {
  var key = request.key;
  
  var userProperties = PropertiesService.getUserProperties();
  userProperties.setProperty('dscc.key', key);
  
  return {
    errorCode: 'NONE'
  };
}

/**
 * Resets the auth service.
 */
function resetAuth() {
  var userProperties = PropertiesService.getUserProperties();
  userProperties.deleteProperty('dscc.key');
}

// ============================================================================
// Helper Functions
// ============================================================================

var cc = DataStudioApp.createCommunityConnector();

/**
 * Get API key from user properties
 */
function getApiKey() {
  var userProperties = PropertiesService.getUserProperties();
  return userProperties.getProperty('dscc.key');
}

/**
 * Fetch dataset info from SetuPranali
 */
function fetchDatasetInfo(serverUrl, dataset, apiKey) {
  var url = serverUrl + '/v1/introspection/datasets/' + dataset;
  
  var options = {
    method: 'get',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json'
    },
    muteHttpExceptions: true
  };
  
  var response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() !== 200) {
    throw new Error('Failed to fetch dataset info: ' + response.getContentText());
  }
  
  return JSON.parse(response.getContentText());
}

/**
 * Execute query against SetuPranali
 */
function executeQuery(serverUrl, dataset, dimensions, metrics, filters, limit, apiKey) {
  var url = serverUrl + '/v1/query';
  
  var payload = {
    dataset: dataset,
    dimensions: dimensions,
    metrics: metrics,
    filters: filters,
    limit: limit
  };
  
  var options = {
    method: 'post',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  var response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() !== 200) {
    throw new Error('Query failed: ' + response.getContentText());
  }
  
  return JSON.parse(response.getContentText());
}

/**
 * Map SetuPranali type to Looker Studio data type
 */
function mapDataType(type) {
  var typeMap = {
    'string': 'STRING',
    'varchar': 'STRING',
    'text': 'STRING',
    'number': 'NUMBER',
    'integer': 'NUMBER',
    'int': 'NUMBER',
    'bigint': 'NUMBER',
    'float': 'NUMBER',
    'double': 'NUMBER',
    'decimal': 'NUMBER',
    'numeric': 'NUMBER',
    'boolean': 'BOOLEAN',
    'bool': 'BOOLEAN',
    'date': 'YEAR_MONTH_DAY',
    'timestamp': 'YEAR_MONTH_DAY_SECOND',
    'datetime': 'YEAR_MONTH_DAY_SECOND'
  };
  
  return typeMap[type.toLowerCase()] || 'STRING';
}

/**
 * Format field name as human-readable label
 */
function formatLabel(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .map(function(word) {
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

/**
 * Returns true if this is an admin user.
 * @return {boolean} True if admin
 */
function isAdminUser() {
  return false;
}

