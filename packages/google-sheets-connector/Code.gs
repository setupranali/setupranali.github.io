/**
 * SetuPranali Google Sheets Connector
 * 
 * Apps Script add-on for querying SetuPranali semantic layer
 * directly from Google Sheets.
 * 
 * @license Apache-2.0
 */

// =============================================================================
// Menu & UI
// =============================================================================

/**
 * Creates menu when spreadsheet opens
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('SetuPranali')
    .addItem('Query Builder', 'showQueryBuilder')
    .addItem('Natural Language Query', 'showNLQ')
    .addSeparator()
    .addItem('Refresh Current Query', 'refreshCurrentQuery')
    .addItem('Refresh All Queries', 'refreshAllQueries')
    .addSeparator()
    .addItem('Settings', 'showSettings')
    .addToUi();
}

/**
 * Show query builder sidebar
 */
function showQueryBuilder() {
  const html = HtmlService.createHtmlOutputFromFile('QueryBuilder')
    .setTitle('SetuPranali Query Builder')
    .setWidth(350);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Show natural language query dialog
 */
function showNLQ() {
  const html = HtmlService.createHtmlOutputFromFile('NLQ')
    .setTitle('Ask a Question')
    .setWidth(400)
    .setHeight(200);
  SpreadsheetApp.getUi().showModalDialog(html, 'Natural Language Query');
}

/**
 * Show settings dialog
 */
function showSettings() {
  const html = HtmlService.createHtmlOutputFromFile('Settings')
    .setTitle('SetuPranali Settings')
    .setWidth(400)
    .setHeight(300);
  SpreadsheetApp.getUi().showModalDialog(html, 'Settings');
}

// =============================================================================
// Settings Management
// =============================================================================

/**
 * Get saved settings
 */
function getSettings() {
  const props = PropertiesService.getUserProperties();
  return {
    serverUrl: props.getProperty('SETUPRANALI_SERVER_URL') || '',
    apiKey: props.getProperty('SETUPRANALI_API_KEY') || ''
  };
}

/**
 * Save settings
 */
function saveSettings(serverUrl, apiKey) {
  const props = PropertiesService.getUserProperties();
  props.setProperty('SETUPRANALI_SERVER_URL', serverUrl);
  props.setProperty('SETUPRANALI_API_KEY', apiKey);
  return { success: true };
}

/**
 * Test connection to server
 */
function testConnection() {
  const settings = getSettings();
  
  if (!settings.serverUrl || !settings.apiKey) {
    return { success: false, error: 'Server URL and API key are required' };
  }
  
  try {
    const response = UrlFetchApp.fetch(settings.serverUrl + '/v1/health', {
      method: 'get',
      headers: {
        'X-API-Key': settings.apiKey
      },
      muteHttpExceptions: true
    });
    
    if (response.getResponseCode() === 200) {
      return { success: true, message: 'Connection successful!' };
    } else {
      return { success: false, error: 'Connection failed: ' + response.getResponseCode() };
    }
  } catch (error) {
    return { success: false, error: 'Connection error: ' + error.message };
  }
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get list of available datasets
 */
function getDatasets() {
  const settings = getSettings();
  
  if (!settings.serverUrl || !settings.apiKey) {
    throw new Error('Please configure SetuPranali settings first');
  }
  
  const response = UrlFetchApp.fetch(settings.serverUrl + '/v1/introspection/datasets', {
    method: 'get',
    headers: {
      'X-API-Key': settings.apiKey
    }
  });
  
  const data = JSON.parse(response.getContentText());
  return data.datasets || [];
}

/**
 * Get schema for a dataset
 */
function getDatasetSchema(datasetId) {
  const settings = getSettings();
  
  const response = UrlFetchApp.fetch(settings.serverUrl + '/v1/introspection/datasets/' + datasetId, {
    method: 'get',
    headers: {
      'X-API-Key': settings.apiKey
    }
  });
  
  return JSON.parse(response.getContentText());
}

/**
 * Execute a semantic query
 */
function executeQuery(query) {
  const settings = getSettings();
  
  const response = UrlFetchApp.fetch(settings.serverUrl + '/v1/query', {
    method: 'post',
    headers: {
      'X-API-Key': settings.apiKey,
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify(query)
  });
  
  return JSON.parse(response.getContentText());
}

/**
 * Execute a natural language query
 */
function executeNLQ(question, dataset) {
  const settings = getSettings();
  
  const payload = { question: question };
  if (dataset) {
    payload.dataset = dataset;
  }
  
  const response = UrlFetchApp.fetch(settings.serverUrl + '/v1/nlq', {
    method: 'post',
    headers: {
      'X-API-Key': settings.apiKey,
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify(payload)
  });
  
  return JSON.parse(response.getContentText());
}

// =============================================================================
// Sheet Operations
// =============================================================================

/**
 * Run query and insert results into active sheet
 */
function runQueryToSheet(queryConfig) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const startCell = sheet.getActiveCell();
  
  try {
    // Execute query
    const result = executeQuery(queryConfig);
    
    if (!result.data || result.data.length === 0) {
      SpreadsheetApp.getUi().alert('Query returned no results');
      return;
    }
    
    // Get columns from query
    const columns = [...(queryConfig.dimensions || []), ...(queryConfig.metrics || [])];
    
    // Prepare data
    const headers = [columns];
    const rows = result.data.map(row => columns.map(col => row[col] ?? ''));
    const allData = [...headers, ...rows];
    
    // Get range
    const numRows = allData.length;
    const numCols = columns.length;
    const range = sheet.getRange(
      startCell.getRow(),
      startCell.getColumn(),
      numRows,
      numCols
    );
    
    // Set values
    range.setValues(allData);
    
    // Format headers
    const headerRange = sheet.getRange(
      startCell.getRow(),
      startCell.getColumn(),
      1,
      numCols
    );
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#4285f4');
    headerRange.setFontColor('white');
    
    // Store query metadata as developer metadata
    sheet.addDeveloperMetadata(
      'SETUPRANALI_QUERY_' + startCell.getA1Notation(),
      JSON.stringify({
        query: queryConfig,
        range: range.getA1Notation(),
        timestamp: new Date().toISOString()
      })
    );
    
    return { success: true, rows: result.data.length };
    
  } catch (error) {
    SpreadsheetApp.getUi().alert('Query Error: ' + error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Run NLQ and insert results
 */
function runNLQToSheet(question, dataset) {
  try {
    const result = executeNLQ(question, dataset);
    
    if (result.query) {
      return runQueryToSheet(result.query);
    } else {
      SpreadsheetApp.getUi().alert('Could not understand the question');
      return { success: false };
    }
  } catch (error) {
    SpreadsheetApp.getUi().alert('NLQ Error: ' + error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Refresh query at current cell
 */
function refreshCurrentQuery() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const cell = sheet.getActiveCell();
  
  // Find metadata for this location
  const metadata = sheet.getDeveloperMetadata();
  
  for (const meta of metadata) {
    if (meta.getKey().startsWith('SETUPRANALI_QUERY_')) {
      const data = JSON.parse(meta.getValue());
      const range = sheet.getRange(data.range);
      
      if (range.getRow() === cell.getRow() && range.getColumn() === cell.getColumn()) {
        // Re-run query
        const result = executeQuery(data.query);
        
        // Update data (preserve headers)
        const columns = [...(data.query.dimensions || []), ...(data.query.metrics || [])];
        const rows = result.data.map(row => columns.map(col => row[col] ?? ''));
        
        // Clear old data
        range.offset(1, 0, range.getNumRows() - 1, range.getNumColumns()).clearContent();
        
        // Set new data
        if (rows.length > 0) {
          const dataRange = sheet.getRange(
            range.getRow() + 1,
            range.getColumn(),
            rows.length,
            columns.length
          );
          dataRange.setValues(rows);
        }
        
        // Update metadata timestamp
        meta.setValue(JSON.stringify({
          ...data,
          timestamp: new Date().toISOString()
        }));
        
        SpreadsheetApp.getUi().alert('Refreshed ' + rows.length + ' rows');
        return;
      }
    }
  }
  
  SpreadsheetApp.getUi().alert('No SetuPranali query found at this location');
}

/**
 * Refresh all queries in sheet
 */
function refreshAllQueries() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const metadata = sheet.getDeveloperMetadata();
  
  let count = 0;
  
  for (const meta of metadata) {
    if (meta.getKey().startsWith('SETUPRANALI_QUERY_')) {
      try {
        const data = JSON.parse(meta.getValue());
        const result = executeQuery(data.query);
        
        const range = sheet.getRange(data.range);
        const columns = [...(data.query.dimensions || []), ...(data.query.metrics || [])];
        const rows = result.data.map(row => columns.map(col => row[col] ?? ''));
        
        // Clear and set new data
        range.offset(1, 0, range.getNumRows() - 1, range.getNumColumns()).clearContent();
        
        if (rows.length > 0) {
          const dataRange = sheet.getRange(
            range.getRow() + 1,
            range.getColumn(),
            rows.length,
            columns.length
          );
          dataRange.setValues(rows);
        }
        
        count++;
      } catch (error) {
        console.error('Failed to refresh query:', error);
      }
    }
  }
  
  SpreadsheetApp.getUi().alert('Refreshed ' + count + ' queries');
}

// =============================================================================
// Custom Functions
// =============================================================================

/**
 * Query SetuPranali dataset
 * 
 * @param {string} dataset Dataset ID
 * @param {string} dimensions Comma-separated dimensions
 * @param {string} metrics Comma-separated metrics
 * @param {number} limit Maximum rows (optional)
 * @return Query results as 2D array
 * @customfunction
 */
function SETUPRANALI(dataset, dimensions, metrics, limit) {
  const query = {
    dataset: dataset,
    dimensions: dimensions ? dimensions.split(',').map(d => d.trim()) : [],
    metrics: metrics ? metrics.split(',').map(m => m.trim()) : [],
    limit: limit || 1000
  };
  
  const result = executeQuery(query);
  
  if (!result.data || result.data.length === 0) {
    return [['No data']];
  }
  
  const columns = [...query.dimensions, ...query.metrics];
  const headers = [columns];
  const rows = result.data.map(row => columns.map(col => row[col] ?? ''));
  
  return [...headers, ...rows];
}

/**
 * Get a single metric value
 * 
 * @param {string} dataset Dataset ID
 * @param {string} metric Metric name
 * @param {string} filters JSON filters (optional)
 * @return Metric value
 * @customfunction
 */
function SETUPRANALI_METRIC(dataset, metric, filters) {
  const query = {
    dataset: dataset,
    dimensions: [],
    metrics: [metric],
    limit: 1
  };
  
  if (filters) {
    query.filters = JSON.parse(filters);
  }
  
  const result = executeQuery(query);
  
  if (!result.data || result.data.length === 0) {
    return 0;
  }
  
  return result.data[0][metric] || 0;
}

/**
 * Ask a natural language question
 * 
 * @param {string} question Natural language question
 * @param {string} dataset Dataset ID (optional)
 * @return Query results as 2D array
 * @customfunction
 */
function SETUPRANALI_ASK(question, dataset) {
  const result = executeNLQ(question, dataset);
  
  if (!result.data || result.data.length === 0) {
    return [['No data']];
  }
  
  const columns = Object.keys(result.data[0]);
  const headers = [columns];
  const rows = result.data.map(row => columns.map(col => row[col] ?? ''));
  
  return [...headers, ...rows];
}

