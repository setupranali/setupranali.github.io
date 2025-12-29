# SetuPranali Metabase Driver - Marketplace Listing

This document contains the information required for Metabase Marketplace certification.

---

## Driver Information

### Basic Info

| Field | Value |
|-------|-------|
| **Driver Name** | SetuPranali |
| **Version** | 1.0.0 |
| **Metabase Version** | 0.47+ |
| **License** | Apache 2.0 |
| **Maintainer** | SetuPranali Community |
| **Repository** | https://github.com/setupranali/setupranali.github.io |
| **Documentation** | https://setupranali.github.io/integrations/bi-tools/metabase/ |

### Description

**Short Description:**
Connect Metabase to SetuPranali semantic layer for governed metrics and dimensions.

**Long Description:**
SetuPranali driver for Metabase enables seamless integration with the SetuPranali semantic layer. Query your governed metrics and dimensions directly from Metabase with automatic Row-Level Security (RLS), caching, and multi-tenant support.

**Key Features:**
- Native semantic layer integration
- Automatic Row-Level Security
- Query caching with Redis
- Multi-tenant support
- GraphQL and REST API support
- Natural Language Queries (NLQ)

### Categories

- Analytics
- Semantic Layer
- Data Governance
- BI Integration

### Tags

`semantic-layer`, `metrics`, `dimensions`, `rls`, `multi-tenant`, `caching`, `analytics`

---

## Technical Requirements

### System Requirements

- Metabase 0.47 or higher
- Java 11 or higher (for driver compilation)
- SetuPranali server accessible from Metabase

### Dependencies

```clojure
:dependencies [[org.clojure/clojure "1.11.1"]
               [org.clojure/data.json "2.4.0"]
               [clj-http "3.12.3"]]
```

### Installation

1. Download the driver JAR from GitHub Releases
2. Copy to Metabase plugins directory
3. Restart Metabase
4. Configure connection

### Connection Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Host | Yes | SetuPranali server hostname |
| Port | Yes | Server port (default: 8080) |
| API Key | Yes | Authentication API key |
| Use SSL | No | Enable HTTPS connection |
| Tenant ID | No | Multi-tenant identifier |

---

## Certification Checklist

### Required Features

- [x] Basic connectivity
- [x] Schema introspection
- [x] Query execution
- [x] Error handling
- [x] Connection testing
- [x] SSL/TLS support

### Optional Features

- [x] Native query support
- [x] Variable substitution
- [x] Custom aggregations
- [x] Time dimension support
- [ ] Database actions (write operations)

### Quality Requirements

- [x] Unit tests
- [x] Integration tests
- [x] Documentation
- [x] Error messages
- [x] Logging

---

## Screenshots

### Connection Setup

```
┌─────────────────────────────────────────────────────┐
│ Add Database                                         │
├─────────────────────────────────────────────────────┤
│ Database type: SetuPranali                          │
│                                                      │
│ Display name: [Production Metrics            ]      │
│                                                      │
│ Host:         [metrics.company.com           ]      │
│ Port:         [8080                          ]      │
│ API Key:      [sk_live_xxxxx                 ]      │
│                                                      │
│ ☑ Use SSL                                           │
│                                                      │
│ [Test Connection]                    [Save]         │
└─────────────────────────────────────────────────────┘
```

### Schema Browser

```
┌─────────────────────────────────────────────────────┐
│ Tables                                               │
├─────────────────────────────────────────────────────┤
│ ▼ orders                                            │
│   ├─ order_date (date)                              │
│   ├─ region (string)                                │
│   ├─ product_category (string)                      │
│   ├─ revenue (number) [metric]                      │
│   └─ order_count (number) [metric]                  │
│                                                      │
│ ▼ customers                                         │
│   ├─ customer_id (string)                           │
│   ├─ signup_date (date)                             │
│   └─ lifetime_value (number) [metric]               │
└─────────────────────────────────────────────────────┘
```

---

## Support

### Community Support

- GitHub Issues: https://github.com/setupranali/setupranali.github.io/issues
- Discord: https://discord.gg/setupranali
- Documentation: https://setupranali.github.io

### Commercial Support

Available through SetuPranali Enterprise (contact community@setupranali.io)

---

## Changelog

### v1.0.0 (2025-12-29)

- Initial release
- Full Metabase 0.47+ support
- Schema introspection
- Query execution
- SSL/TLS support
- Multi-tenant support

