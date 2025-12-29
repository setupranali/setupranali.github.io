# SetuPranali Excel Add-in

Query SetuPranali semantic layer directly from Microsoft Excel.

## Features

- **Native Excel Integration**: Query builder in Excel task pane
- **Schema Browser**: View available datasets, dimensions, and metrics
- **Query Builder**: Visual interface to build semantic queries
- **Data Refresh**: Refresh queries to get latest data
- **Formatted Tables**: Results formatted as Excel tables

## Installation

### From Microsoft AppSource (Coming Soon)

1. Open Excel
2. Go to **Insert** > **Add-ins** > **Get Add-ins**
3. Search for "SetuPranali"
4. Click **Add**

### Manual Installation (Sideloading)

1. Download `manifest.xml`
2. Follow [Microsoft's sideloading guide](https://docs.microsoft.com/en-us/office/dev/add-ins/testing/sideload-office-add-ins-for-testing)

### For Developers

```bash
# Clone repository
git clone https://github.com/setupranali/setupranali.github.io.git
cd packages/excel-addin

# Install dependencies
npm install

# Start development server
npm start

# Sideload in Excel
npm run sideload
```

## Configuration

1. Click **SetuPranali** button in ribbon
2. Go to **Settings** tab
3. Enter:
   - **Server URL**: Your SetuPranali server (e.g., `https://your-server.com`)
   - **API Key**: Your API key
4. Click **Test Connection**
5. Click **Save Settings**

## Usage

### Running a Query

1. Select a **Dataset** from dropdown
2. Check the **Dimensions** to include
3. Check the **Metrics** to include
4. Optionally set **Date Range** and **Row Limit**
5. Click **Run Query**
6. Data is inserted as a formatted Excel table

### Refreshing Data

Click **Refresh** button in ribbon to refresh all SetuPranali queries.

## Example

```
1. Dataset: orders
2. Dimensions: order_date, region
3. Metrics: revenue, order_count
4. Click "Run Query"

Result in Excel:
+------------+--------+---------+-------------+
| order_date | region | revenue | order_count |
+------------+--------+---------+-------------+
| 2025-01-01 | US     | 15000   | 120         |
| 2025-01-01 | EU     | 12000   | 95          |
| 2025-01-02 | US     | 18000   | 145         |
+------------+--------+---------+-------------+
```

## System Requirements

- Microsoft Excel 2016 or later
- Excel for Mac 2016 or later
- Excel Online
- Windows 10 or later / macOS 10.14 or later

## Custom Functions (Coming Soon)

Use SetuPranali directly in cell formulas:

```excel
=SETUPRANALI.QUERY("orders", "region", "revenue")
=SETUPRANALI.METRIC("orders", "total_revenue")
=SETUPRANALI.NLQ("What was revenue last month?")
```

## Troubleshooting

### Connection Failed

1. Verify server URL is correct (include https://)
2. Check API key is valid
3. Ensure server is accessible from your network

### No Datasets Showing

1. Check API key has access to datasets
2. Verify server is running
3. Check browser console for errors

### Data Not Inserting

1. Ensure worksheet is not protected
2. Check cell A1 is available
3. Verify you have write permissions

## Development

### Project Structure

```
excel-addin/
├── manifest.xml          # Office Add-in manifest
├── src/
│   ├── taskpane.html    # Task pane UI
│   ├── taskpane.js      # Task pane logic
│   └── functions.js     # Custom functions (future)
├── assets/
│   └── icons/           # Add-in icons
└── package.json
```

### Building

```bash
npm run build
```

### Testing

```bash
npm test
```

## License

Apache 2.0 - See [LICENSE](../../LICENSE)

