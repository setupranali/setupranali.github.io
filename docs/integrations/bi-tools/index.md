# BI Tools

Connect your visualization tools to SetuPranali.

---

## Supported Tools

<div class="grid cards" markdown>

-   :material-microsoft:{ .lg .middle } **Power BI**

    ---

    Native OData integration. Works with Desktop and Service.

    [:octicons-arrow-right-24: Power BI Guide](powerbi.md)

-   :material-chart-box:{ .lg .middle } **Tableau**

    ---

    Web Data Connector for Desktop, Server, and Cloud.

    [:octicons-arrow-right-24: Tableau Guide](tableau.md)

-   :material-api:{ .lg .middle } **REST API**

    ---

    Connect any tool via REST API.

    [:octicons-arrow-right-24: REST API](rest-api.md)

</div>

---

## Protocol Comparison

| Protocol | Tools | Best For |
|----------|-------|----------|
| **OData** | Power BI, Excel | Microsoft ecosystem, native refresh |
| **WDC** | Tableau | Tableau Desktop/Server |
| **REST** | Any | Custom integrations, scripts |

---

## Common Configuration

### API Key

All connections require an API key:

| Tool | Configuration |
|------|---------------|
| Power BI | HTTP header: `X-API-Key` |
| Tableau | WDC authentication field |
| REST | Header or query parameter |

### Base URL

```
http://your-server:8080
```

For production, use HTTPS:

```
https://bi-api.yourdomain.com
```

---

## Quick Reference

### Power BI OData URL

```
http://localhost:8080/odata/{dataset}
```

### Tableau WDC URL

```
http://localhost:8080/wdc/
```

### REST Query URL

```
POST http://localhost:8080/v1/query
```

