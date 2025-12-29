# SetuPranali VS Code Extension

Official VS Code extension for [SetuPranali](https://setupranali.github.io) - the semantic layer for BI tools.

## Features

### IntelliSense for Catalog Files

- **Auto-completion** for datasets, dimensions, metrics, and joins
- **Hover information** showing field details
- **Go to definition** for quick navigation
- **SQL function suggestions** with snippets

### Real-Time Validation

- YAML syntax validation
- Schema validation for catalog structure
- Duplicate ID detection
- Reference validation for joins
- Server-side validation (optional)

### Snippets

Quick snippets for common patterns:

| Prefix | Description |
|--------|-------------|
| `setu-catalog` | Complete catalog template |
| `setu-dataset` | New dataset definition |
| `setu-dim` | New dimension |
| `setu-metric-count` | Count metric |
| `setu-metric-sum` | Sum metric |
| `setu-metric-avg` | Average metric |
| `setu-join` | Semantic join |
| `setu-calc-metric` | Calculated metric |
| `setu-rls` | Row-level security field |

### Import From Other Tools

Import existing semantic models:

- **dbt** - Import from manifest.json
- **LookML** - Import Looker views and explores
- **Cube.js** - Import Cube schemas

### Catalog Explorer

Tree view showing:
- All datasets in your catalog
- Dimensions per dataset
- Metrics per dataset

## Installation

### From VS Code Marketplace

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "SetuPranali"
4. Click Install

### From VSIX File

```bash
# Download the VSIX file
curl -L -o setupranali-vscode.vsix https://github.com/setupranali/setupranali.github.io/releases/latest/download/setupranali-vscode.vsix

# Install
code --install-extension setupranali-vscode.vsix
```

## Configuration

Configure the extension in VS Code settings:

```json
{
  "setupranali.serverUrl": "http://localhost:8080",
  "setupranali.apiKey": "your-api-key",
  "setupranali.enableValidation": true,
  "setupranali.enableAutoComplete": true,
  "setupranali.catalogPath": "catalog.yaml"
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `serverUrl` | `http://localhost:8080` | SetuPranali server URL |
| `apiKey` | `""` | API key for authentication |
| `enableValidation` | `true` | Enable real-time validation |
| `enableAutoComplete` | `true` | Enable IntelliSense |
| `catalogPath` | `catalog.yaml` | Path to catalog file |

## Usage

### Creating a New Catalog

1. Create a new file named `catalog.yaml`
2. Type `setu-catalog` and press Tab
3. Fill in the template

### Adding Datasets

Type `setu-dataset` in your catalog file for a dataset template:

```yaml
- id: orders
  name: Orders
  description: Order transactions
  sql: SELECT * FROM orders
  
  dimensions:
    - name: order_id
      sql: order_id
      type: string
  
  metrics:
    - name: count
      sql: COUNT(*)
```

### Validating Your Catalog

- Errors appear in the Problems panel as you type
- Run "SetuPranali: Validate Catalog" from Command Palette (Ctrl+Shift+P)

### Importing from dbt

1. Run "SetuPranali: Import from dbt" from Command Palette
2. Select your `manifest.json` file
3. The extension generates a `catalog.yaml`

## Commands

| Command | Description |
|---------|-------------|
| `SetuPranali: Validate Catalog` | Validate the current catalog file |
| `SetuPranali: Preview Query` | Generate a sample query |
| `SetuPranali: Sync with Server` | Sync catalog with SetuPranali server |
| `SetuPranali: Import from dbt` | Import dbt manifest |
| `SetuPranali: Import from LookML` | Import LookML project |
| `SetuPranali: Import from Cube.js` | Import Cube.js schemas |

## Keyboard Shortcuts

| Shortcut | Command |
|----------|---------|
| `Ctrl+Shift+V` | Validate Catalog |

## Requirements

- VS Code 1.74.0 or later
- Node.js 16+ (for development)

## Building from Source

```bash
# Clone the repository
git clone https://github.com/setupranali/setupranali.github.io.git
cd setupranali.github.io/extensions/vscode

# Install dependencies
npm install

# Compile
npm run compile

# Package
npm run package
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](https://github.com/setupranali/setupranali.github.io/blob/main/CONTRIBUTING.md).

## License

Apache 2.0 - see [LICENSE](https://github.com/setupranali/setupranali.github.io/blob/main/LICENSE).

## Support

- [Documentation](https://setupranali.github.io)
- [GitHub Issues](https://github.com/setupranali/setupranali.github.io/issues)
- [Discord](https://discord.gg/setupranali)

