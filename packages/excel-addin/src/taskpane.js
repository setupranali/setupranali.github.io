/**
 * SetuPranali Excel Add-in
 * 
 * Query SetuPranali semantic layer directly from Excel.
 */

// Configuration
let config = {
    serverUrl: '',
    apiKey: ''
};

// State
let datasets = [];
let currentSchema = null;

// Initialize when Office is ready
Office.onReady((info) => {
    if (info.host === Office.HostType.Excel) {
        loadSettings();
        initializeUI();
    }
});

/**
 * Initialize UI event handlers
 */
function initializeUI() {
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    
    // Dataset selection
    document.getElementById('dataset-select').addEventListener('change', onDatasetChange);
    
    // Run query
    document.getElementById('run-query').addEventListener('click', runQuery);
    
    // Settings
    document.getElementById('test-connection').addEventListener('click', testConnection);
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    
    // Load datasets if configured
    if (config.serverUrl && config.apiKey) {
        loadDatasets();
    }
}

/**
 * Switch between tabs
 */
function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(`${tabId}-tab`).classList.add('active');
}

/**
 * Load settings from Office storage
 */
function loadSettings() {
    config.serverUrl = Office.context.roamingSettings.get('serverUrl') || '';
    config.apiKey = Office.context.roamingSettings.get('apiKey') || '';
    
    document.getElementById('server-url').value = config.serverUrl;
    document.getElementById('api-key').value = config.apiKey;
}

/**
 * Save settings to Office storage
 */
function saveSettings() {
    config.serverUrl = document.getElementById('server-url').value.trim();
    config.apiKey = document.getElementById('api-key').value.trim();
    
    Office.context.roamingSettings.set('serverUrl', config.serverUrl);
    Office.context.roamingSettings.set('apiKey', config.apiKey);
    
    Office.context.roamingSettings.saveAsync((result) => {
        if (result.status === Office.AsyncResultStatus.Succeeded) {
            showStatus('Settings saved successfully', 'success');
            loadDatasets();
        } else {
            showStatus('Failed to save settings', 'error');
        }
    });
}

/**
 * Test connection to SetuPranali server
 */
async function testConnection() {
    const url = document.getElementById('server-url').value.trim();
    const key = document.getElementById('api-key').value.trim();
    
    if (!url || !key) {
        showStatus('Please enter server URL and API key', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${url}/v1/health`, {
            headers: {
                'X-API-Key': key
            }
        });
        
        if (response.ok) {
            showStatus('Connection successful!', 'success');
        } else {
            showStatus(`Connection failed: ${response.status}`, 'error');
        }
    } catch (error) {
        showStatus(`Connection error: ${error.message}`, 'error');
    }
}

/**
 * Load available datasets
 */
async function loadDatasets() {
    if (!config.serverUrl || !config.apiKey) {
        return;
    }
    
    try {
        const response = await fetch(`${config.serverUrl}/v1/introspection/datasets`, {
            headers: {
                'X-API-Key': config.apiKey
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            datasets = data.datasets || [];
            populateDatasetSelect();
        }
    } catch (error) {
        console.error('Failed to load datasets:', error);
    }
}

/**
 * Populate dataset dropdown
 */
function populateDatasetSelect() {
    const select = document.getElementById('dataset-select');
    select.innerHTML = '<option value="">Select dataset...</option>';
    
    datasets.forEach(ds => {
        const option = document.createElement('option');
        option.value = ds.id;
        option.textContent = ds.name || ds.id;
        select.appendChild(option);
    });
}

/**
 * Handle dataset selection change
 */
async function onDatasetChange(event) {
    const datasetId = event.target.value;
    
    if (!datasetId) {
        document.getElementById('dimensions-list').innerHTML = '';
        document.getElementById('metrics-list').innerHTML = '';
        document.getElementById('run-query').disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`${config.serverUrl}/v1/introspection/datasets/${datasetId}`, {
            headers: {
                'X-API-Key': config.apiKey
            }
        });
        
        if (response.ok) {
            currentSchema = await response.json();
            populateDimensions(currentSchema.dimensions || []);
            populateMetrics(currentSchema.metrics || []);
            document.getElementById('run-query').disabled = false;
        }
    } catch (error) {
        console.error('Failed to load schema:', error);
        showStatus(`Failed to load schema: ${error.message}`, 'error');
    }
}

/**
 * Populate dimensions checkboxes
 */
function populateDimensions(dimensions) {
    const container = document.getElementById('dimensions-list');
    container.innerHTML = '';
    
    dimensions.forEach(dim => {
        const item = document.createElement('label');
        item.className = 'checkbox-item';
        item.innerHTML = `
            <input type="checkbox" name="dimension" value="${dim.name}">
            ${dim.name}
        `;
        container.appendChild(item);
    });
}

/**
 * Populate metrics checkboxes
 */
function populateMetrics(metrics) {
    const container = document.getElementById('metrics-list');
    container.innerHTML = '';
    
    metrics.forEach(met => {
        const item = document.createElement('label');
        item.className = 'checkbox-item';
        item.innerHTML = `
            <input type="checkbox" name="metric" value="${met.name}" checked>
            ${met.name}
        `;
        container.appendChild(item);
    });
}

/**
 * Run query and insert results into Excel
 */
async function runQuery() {
    const dataset = document.getElementById('dataset-select').value;
    const dimensions = getSelectedValues('dimension');
    const metrics = getSelectedValues('metric');
    const limit = parseInt(document.getElementById('limit').value) || 1000;
    
    if (!dataset) {
        showStatus('Please select a dataset', 'error');
        return;
    }
    
    if (metrics.length === 0) {
        showStatus('Please select at least one metric', 'error');
        return;
    }
    
    // Build query
    const query = {
        dataset: dataset,
        dimensions: dimensions,
        metrics: metrics,
        limit: limit
    };
    
    // Add date filters if set
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;
    
    if (dateFrom || dateTo) {
        query.filters = {};
        if (dateFrom) query.filters.date_from = dateFrom;
        if (dateTo) query.filters.date_to = dateTo;
    }
    
    // Show loading
    const button = document.getElementById('run-query');
    button.disabled = true;
    button.querySelector('.loading').classList.remove('hidden');
    
    try {
        const response = await fetch(`${config.serverUrl}/v1/query`, {
            method: 'POST',
            headers: {
                'X-API-Key': config.apiKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(query)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || `Query failed: ${response.status}`);
        }
        
        const result = await response.json();
        await insertDataIntoExcel(result.data, [...dimensions, ...metrics]);
        
        showStatus(`Inserted ${result.data.length} rows`, 'success');
        
    } catch (error) {
        showStatus(`Query failed: ${error.message}`, 'error');
    } finally {
        button.disabled = false;
        button.querySelector('.loading').classList.add('hidden');
    }
}

/**
 * Insert data into Excel worksheet
 */
async function insertDataIntoExcel(data, columns) {
    return Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getActiveWorksheet();
        const range = sheet.getRange('A1');
        
        // Prepare data with headers
        const headers = [columns];
        const rows = data.map(row => columns.map(col => row[col] ?? ''));
        const allData = [...headers, ...rows];
        
        // Get range for data
        const numRows = allData.length;
        const numCols = columns.length;
        const dataRange = sheet.getRange(`A1:${getColumnLetter(numCols)}${numRows}`);
        
        // Set values
        dataRange.values = allData;
        
        // Format headers
        const headerRange = sheet.getRange(`A1:${getColumnLetter(numCols)}1`);
        headerRange.format.font.bold = true;
        headerRange.format.fill.color = '#0078d4';
        headerRange.format.font.color = 'white';
        
        // Auto-fit columns
        dataRange.format.autofitColumns();
        
        // Create table
        const table = sheet.tables.add(dataRange, true);
        table.name = `SetuPranali_${Date.now()}`;
        table.style = 'TableStyleMedium2';
        
        await context.sync();
    });
}

/**
 * Get selected checkbox values
 */
function getSelectedValues(name) {
    const checkboxes = document.querySelectorAll(`input[name="${name}"]:checked`);
    return Array.from(checkboxes).map(cb => cb.value);
}

/**
 * Convert column number to letter
 */
function getColumnLetter(num) {
    let letter = '';
    while (num > 0) {
        const mod = (num - 1) % 26;
        letter = String.fromCharCode(65 + mod) + letter;
        num = Math.floor((num - 1) / 26);
    }
    return letter;
}

/**
 * Show status message
 */
function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status ${type}`;
    status.classList.remove('hidden');
    
    setTimeout(() => {
        status.classList.add('hidden');
    }, 5000);
}

/**
 * Refresh all SetuPranali queries in workbook
 */
async function refreshAllQueries() {
    return Excel.run(async (context) => {
        const tables = context.workbook.tables;
        tables.load('items/name');
        
        await context.sync();
        
        const setupranaliTables = tables.items.filter(t => t.name.startsWith('SetuPranali_'));
        
        // TODO: Implement table refresh logic
        // This would require storing query metadata with each table
        
        await context.sync();
    });
}

// Expose function for ribbon button
window.refreshAllQueries = refreshAllQueries;

