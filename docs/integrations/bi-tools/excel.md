# Microsoft Excel Integration

Query SetuPranali semantic layer directly from Microsoft Excel.

---

## Overview

The SetuPranali Excel Add-in provides:

- **Query Builder**: Visual interface in Excel task pane
- **Refresh Queries**: Update data with one click
- **Custom Functions**: Use formulas (coming soon)
- **Formatted Tables**: Results as Excel tables

---

## Installation

### From Microsoft AppSource (Coming Soon)

1. Open Excel
2. Go to **Insert** > **Add-ins** > **Get Add-ins**
3. Search for "SetuPranali"
4. Click **Add**

### Manual Installation

1. Download `manifest.xml` from [GitHub releases](https://github.com/setupranali/setupranali.github.io/releases)
2. Follow [Microsoft's sideloading guide](https://docs.microsoft.com/en-us/office/dev/add-ins/testing/sideload-office-add-ins-for-testing)

---

## Configuration

1. Click **SetuPranali** button in the Data tab ribbon
2. Go to **Settings** tab in the task pane
3. Enter:
   - **Server URL**: Your SetuPranali server (e.g., `https://your-server.com`)
   - **API Key**: Your API key
4. Click **Test Connection**
5. Click **Save Settings**

---

## Usage

### Query Builder

1. Click **SetuPranali** > **Query** in ribbon
2. Select a **Dataset** from dropdown
3. Check the **Dimensions** to include
4. Check the **Metrics** to include
5. Optionally set:
   - **Date Range**: Filter by date
   - **Row Limit**: Maximum rows to return
6. Click **Run Query**

Results are inserted as a formatted Excel table at the active cell.

### Refreshing Data

- **Single Query**: Select the table, click **Refresh**
- **All Queries**: Click **Refresh All** in ribbon

---

## Example

```
Configuration:
  Dataset: orders
  Dimensions: order_date, region
  Metrics: revenue, order_count
  Limit: 1000

Result in Excel:
┌────────────┬────────┬─────────┬─────────────┐
│ order_date │ region │ revenue │ order_count │
├────────────┼────────┼─────────┼─────────────┤
│ 2025-01-01 │ US     │ 15000   │ 120         │
│ 2025-01-01 │ EU     │ 12000   │ 95          │
│ 2025-01-02 │ US     │ 18000   │ 145         │
└────────────┴────────┴─────────┴─────────────┘
```

---

## Custom Functions (Coming Soon)

Use SetuPranali directly in cell formulas:

```excel
=SETUPRANALI.QUERY("orders", "region", "revenue")

=SETUPRANALI.METRIC("orders", "total_revenue")

=SETUPRANALI.NLQ("What was revenue last month?")
```

---

## System Requirements

- Microsoft Excel 2016 or later
- Excel for Mac 2016 or later
- Excel Online
- Windows 10 or later / macOS 10.14 or later

---

## Troubleshooting

### Connection Failed

1. Verify server URL is correct (include https://)
2. Check API key is valid
3. Ensure server is accessible from your network
4. Check firewall settings

### No Datasets Showing

1. Verify connection is configured
2. Check API key has access to datasets
3. Click refresh icon in dataset dropdown

### Data Not Inserting

1. Ensure worksheet is not protected
2. Check cell A1 is available (or select different cell)
3. Verify you have write permissions to workbook

### Add-in Not Loading

1. Check Excel version is 2016 or later
2. Try clearing Office cache
3. Re-install the add-in

---

## Security

- API keys are stored in Office roaming settings
- Keys sync across devices via Microsoft account
- All requests use HTTPS
- No data is stored by the add-in

---

## Source Code

The Excel Add-in source code is available at:

```
packages/excel-addin/
├── manifest.xml          # Office Add-in manifest
├── src/
│   ├── taskpane.html    # Task pane UI
│   └── taskpane.js      # Task pane logic
└── README.md
```

---

## Support

- [GitHub Issues](https://github.com/setupranali/setupranali.github.io/issues)
- [Documentation](https://setupranali.github.io)
- [Discord Community](https://discord.gg/setupranali)

