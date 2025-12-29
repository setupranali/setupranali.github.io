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

-   :simple-apachesuperset:{ .lg .middle } **Apache Superset**

    ---

    REST API and SQL Lab integration for open-source BI.

    [:octicons-arrow-right-24: Superset Guide](superset.md)

-   :material-google-analytics:{ .lg .middle } **Looker Studio**

    ---

    Community Connector for Google's free BI tool.

    [:octicons-arrow-right-24: Looker Studio Guide](looker-studio.md)

-   :simple-metabase:{ .lg .middle } **Metabase**

    ---

    **Native driver plugin** for seamless Metabase integration.

    [:octicons-arrow-right-24: Metabase Guide](metabase.md)

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
| **Native Driver** | Metabase | Seamless Metabase integration |
| **REST** | Superset, Looker Studio, Any | Open-source tools, custom integrations |
| **Community Connector** | Looker Studio | Google ecosystem |

---

## Tool Categories

### Enterprise BI

| Tool | Integration | Row-Level Security | Caching |
|------|-------------|-------------------|---------|
| Power BI | ✅ Native OData | ✅ Automatic | ✅ Redis |
| Tableau | ✅ WDC | ✅ Automatic | ✅ Redis |

### Open Source BI

| Tool | Integration | Row-Level Security | Caching |
|------|-------------|-------------------|---------|
| Apache Superset | ✅ REST API | ✅ Automatic | ✅ Redis |
| Metabase | ✅ **Native Driver** | ✅ Automatic | ✅ Redis |
| Looker Studio | ✅ Community Connector | ✅ Automatic | ✅ Redis |

---

## Common Configuration

### API Key

All connections require an API key:

| Tool | Configuration |
|------|---------------|
| Power BI | HTTP header: `X-API-Key` |
| Tableau | WDC authentication field |
| Superset | Database connection header |
| Looker Studio | Connector configuration |
| Metabase | HTTP driver header |
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

### Superset Database URI

```
setupranali+http://localhost:8080?api_key=your-key
```

### Looker Studio Connector

```
Deploy Apps Script connector and use deployment ID
```

### Metabase Connection

```
HTTP Database: http://localhost:8080/v1
```
