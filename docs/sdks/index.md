# SDKs & Libraries

Official SDKs for integrating with SetuPranali.

---

## Available SDKs

<div class="grid cards" markdown>

-   :fontawesome-brands-python:{ .lg .middle } **Python SDK**

    ---

    Full-featured Python client with sync/async support, pandas integration, and Jupyter widgets.

    [:octicons-arrow-right-24: Python SDK](python.md)

-   :fontawesome-brands-js:{ .lg .middle } **JavaScript/TypeScript SDK**

    ---

    Modern TypeScript SDK for Node.js and browsers with full type definitions.

    [:octicons-arrow-right-24: JavaScript SDK](javascript.md)

-   :material-notebook:{ .lg .middle } **Jupyter Widget**

    ---

    Interactive dataset explorer for Jupyter notebooks.

    [:octicons-arrow-right-24: Jupyter Widget](jupyter.md)

</div>

---

## Quick Comparison

| Feature | Python | JavaScript |
|---------|--------|------------|
| Sync Client | ✅ | ✅ |
| Async Client | ✅ | ✅ |
| DataFrame Support | ✅ pandas | - |
| GraphQL Support | ✅ | ✅ |
| TypeScript Types | - | ✅ |
| Jupyter Integration | ✅ | - |
| Browser Support | - | ✅ |
| Node.js Support | - | ✅ |

---

## Installation

=== "Python"

    ```bash
    pip install setupranali
    
    # With all extras
    pip install setupranali[all]
    ```

=== "JavaScript"

    ```bash
    npm install @setupranali/client
    ```

=== "Yarn"

    ```bash
    yarn add @setupranali/client
    ```

---

## Quick Start

=== "Python"

    ```python
    from setupranali import SetuPranali
    
    client = SetuPranali(
        url="http://localhost:8080",
        api_key="your-api-key"
    )
    
    # Query data
    result = client.query(
        dataset="orders",
        dimensions=["city"],
        metrics=["total_revenue"]
    )
    
    # Convert to DataFrame
    df = result.to_dataframe()
    print(df.head())
    ```

=== "JavaScript"

    ```typescript
    import { SetuPranali } from '@setupranali/client';
    
    const client = new SetuPranali({
      url: 'http://localhost:8080',
      apiKey: 'your-api-key'
    });
    
    // Query data
    const result = await client.query({
      dataset: 'orders',
      dimensions: ['city'],
      metrics: ['total_revenue']
    });
    
    console.log(result.data);
    ```

---

## Coming Soon

- **Go SDK** - For Go applications
- **Rust SDK** - For Rust applications  
- **R Package** - For R and RStudio
- **Excel Add-in** - Native Excel integration
- **Google Sheets** - Apps Script add-on

---

## Contributing SDKs

Want to contribute an SDK for another language? See our [Contributing Guide](../CONTRIBUTING.md).

Requirements:
- Follow the API patterns established in Python/JS SDKs
- Include comprehensive tests
- Provide documentation
- Support all major endpoints

