# SetuPranali

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Stars](https://img.shields.io/github/stars/setupranali/setupranali.github.io?style=social)](https://github.com/setupranali/setupranali.github.io)
[![Discord](https://img.shields.io/discord/your-server-id?label=Discord&logo=discord)](https://discord.gg/setupranali)

<h3 align="center">The Bridge System for BI</h3>

<p align="center">
  <strong>The simplest way to connect Power BI & Tableau to your data warehouse—securely.</strong>
</p>

<p align="center">
  <img src="docs/assets/logo.svg" alt="SetuPranali" width="300">
</p>

<p align="center">
  ⚡ 5-Minute Setup • 🔒 Zero Credential Exposure • 📊 BI-Native Protocols
</p>

---

## What is SetuPranali?

**SetuPranali** means "Bridge System" in Sanskrit — and that's exactly what it does.

It's an open-source semantic gateway that bridges your BI tools (Power BI, Tableau) to your data warehouse. Define metrics once, enforce security automatically, keep using the BI tools you love.

---

## 🌟 Why SetuPranali?

| Problem | Solution |
|---------|----------|
| 🔑 **Credential sprawl** — Every BI tool has database passwords | API key authentication — credentials never leave your server |
| 📊 **Metric drift** — "Revenue" means different things in different dashboards | Define metrics once in YAML, use everywhere |
| 🔒 **No tenant isolation** — Build RLS per-tool, or not at all | Automatic row-level security based on API key |
| 🐢 **Slow dashboards** — Every query hits the database | Redis-based caching with tenant isolation |
| 🔗 **BI lock-in** — Semantic model trapped in one tool | Portable YAML catalog works with any BI tool |

---

## ✨ Features

- **🔌 Native BI Integration** — OData for Power BI, Web Data Connector for Tableau
- **📐 Semantic Layer** — Define dimensions, metrics, and relationships in YAML
- **🛡️ Row-Level Security** — Automatic tenant isolation based on API key
- **⚡ Query Caching** — Redis-backed with tenant isolation
- **🔄 Incremental Refresh** — Load only what's new
- **🗄️ Multi-Source** — PostgreSQL, Snowflake, BigQuery, Databricks, ClickHouse, and more
- **🔐 Encrypted Credentials** — Database credentials encrypted at rest (Fernet/AES)
- **📈 Rate Limiting** — Protect your data warehouse from runaway queries

---

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Run with Docker
docker run -p 8080:8080 adeygifting/connector:latest

# Health check
curl http://localhost:8080/v1/health
```

### From Source

```bash
# Clone the repository
git clone https://github.com/setupranali/setupranali.github.io.git
cd connector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate encryption key
export UBI_SECRET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Start the server
uvicorn app.main:app --port 8080
```

### First Query

```bash
# List datasets
curl http://localhost:8080/v1/datasets

# Query with API key
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-123" \
  -d '{
    "dataset": "orders",
    "dimensions": [{"name": "city"}],
    "metrics": [{"name": "total_revenue"}]
  }'
```

---

## 🆚 How We Compare

Already evaluating semantic layers? Here's how SetuPranali differs:

| Feature | SetuPranali | Cube.dev | dbt Semantic Layer |
|---------|-------------|----------|---------------------|
| **Setup Time** | 5 minutes | Hours | Hours + dbt Cloud |
| **Learning Curve** | YAML config | Cube schema (new DSL) | MetricFlow + dbt |
| **Power BI Support** | ✅ Native OData | 🔶 REST only | 🔶 Limited |
| **Tableau Support** | ✅ Native WDC | 🔶 REST only | 🔶 Limited |
| **Standalone** | ✅ Yes | ✅ Yes | ❌ Requires dbt Cloud |
| **Auto Row-Level Security** | ✅ Via API key | 🔶 Manual config | 🔶 Manual config |
| **Complexity** | Low | High | Medium-High |
| **Best For** | BI teams | API-first products | dbt shops |

### Why Choose SetuPranali?

- **🎯 BI-First** — Built for Power BI and Tableau users, not just developers
- **🪶 Lightweight** — Single Docker container, not a platform
- **⚡ Fast Setup** — YAML config, not a new query language to learn
- **🔓 No Lock-in** — Standard protocols, portable definitions
- **🛡️ Security Built-in** — RLS automatic, not an afterthought

> *"Cube.dev is powerful but complex. dbt requires their cloud. SetuPranali is the simple, standalone bridge for teams that want secure BI access."*

---

## 📖 Documentation

| Resource | Description |
|----------|-------------|
| [**Quick Start Guide**](docs/getting-started/quickstart.md) | Get running in 5 minutes |
| [**Installation**](docs/getting-started/installation.md) | Docker, Kubernetes, source |
| [**Concepts**](docs/concepts/index.md) | Architecture, security model |
| [**API Reference**](docs/api-reference/index.md) | Complete endpoint docs |
| [**Integrations**](docs/integrations/index.md) | BI tools, databases |

---

## 🔌 Supported Integrations

### Data Sources

| Database | Status | Adapter |
|----------|--------|---------|
| PostgreSQL | ✅ Stable | `postgres` |
| MySQL | ✅ Stable | `mysql` |
| Snowflake | ✅ Stable | `snowflake` |
| BigQuery | ✅ Stable | `bigquery` |
| Databricks | ✅ Stable | `databricks` |
| Redshift | ✅ Stable | `redshift` |
| ClickHouse | ✅ Stable | `clickhouse` |
| DuckDB | ✅ Stable | `duckdb` |

### BI Tools

| Tool | Protocol | Status |
|------|----------|--------|
| Power BI | OData | ✅ Native |
| Tableau | Web Data Connector | ✅ Native |
| Excel | OData | ✅ Native |
| Looker Studio | REST API | ✅ Supported |
| Metabase | REST API | ✅ Supported |
| Superset | REST API | ✅ Supported |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         BI TOOLS                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Power BI   │  │   Tableau    │  │   REST API   │       │
└──┴──────┬───────┴──┴──────┬───────┴──┴──────┬───────┴───────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      SETUPRANALI                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   Security Layer                       │  │
│  │  • API Key Authentication  • Row-Level Security       │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   Semantic Layer                       │  │
│  │  • catalog.yaml  • Metrics  • Dimensions  • Relations │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Execution Layer                       │  │
│  │  • Query Engine  • Caching (Redis)  • Rate Limiting   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Snowflake     │ │   PostgreSQL    │ │    BigQuery     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 🤝 Contributing

We love contributions! SetuPranali is built by the community, for the community.

### Ways to Contribute

- 🐛 **Report bugs** — [Open an issue](https://github.com/setupranali/setupranali.github.io/issues/new)
- 💡 **Suggest features** — [Start a discussion](https://github.com/setupranali/setupranali.github.io/discussions)
- 📝 **Improve docs** — Fix typos, add examples, clarify concepts
- 🔌 **Add adapters** — Support new databases
- 🧪 **Write tests** — Increase coverage

### Quick Contribution

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/connector.git

# Create a branch
git checkout -b feature/amazing-feature

# Make changes, then
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature

# Open a Pull Request!
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 🗺️ Roadmap

See our [ROADMAP.md](ROADMAP.md) for planned features and how to influence priorities.

### Coming Soon

- [ ] 🔐 SSO/SAML authentication
- [ ] 📊 Query analytics dashboard
- [ ] 🔄 Trino/Presto adapter
- [ ] 📱 GraphQL API
- [ ] 🌐 Metabase native connector

---

## 💬 Community

Join our growing community!

| Channel | Description |
|---------|-------------|
| [**Discord**](https://discord.gg/setupranali) | Real-time chat, help, and discussions |
| [**GitHub Discussions**](https://github.com/setupranali/setupranali.github.io/discussions) | Feature requests, Q&A, show & tell |
| [**Twitter**](https://twitter.com/setupranali) | Updates and announcements |
| [**Stack Overflow**](https://stackoverflow.com/questions/tagged/setupranali) | Technical Q&A |

See [COMMUNITY.md](COMMUNITY.md) for community guidelines and resources.

---

## 📄 License

SetuPranali is open source under the [Apache License 2.0](LICENSE).

```
Copyright 2024 SetuPranali Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

---

## 🙏 Acknowledgments

Built with ❤️ by the data community. Special thanks to all our [contributors](https://github.com/setupranali/setupranali.github.io/graphs/contributors)!

---

<p align="center">
  <strong>⭐ Star us on GitHub if you find this useful!</strong>
</p>

<p align="center">
  <a href="https://github.com/setupranali/setupranali.github.io">
    <img src="https://img.shields.io/github/stars/setupranali/setupranali.github.io?style=social" alt="GitHub Stars">
  </a>
</p>

<p align="center">
  <sub>SetuPranali — Bridge Your Data, Empower Your BI</sub>
</p>
