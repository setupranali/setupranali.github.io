# Getting Started

Welcome to SetuPranali! This guide will help you go from zero to 
querying data in your BI tool in under 15 minutes.

---

## Prerequisites

Before you begin, ensure you have:

| Requirement | Description |
|-------------|-------------|
| **Docker** | For running the connector (or Python 3.9+ for source install) |
| **Data Source** | Access to a database (PostgreSQL, Snowflake, BigQuery, etc.) |
| **BI Tool** | Power BI, Tableau, or any REST client |

!!! note "No Database Credentials in BI Tools"
    Unlike direct connections, your BI users will never see database credentials.
    All access is controlled through API keys.

---

## Quick Navigation

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Get up and running in 5 minutes with our step-by-step tutorial.

    [:octicons-arrow-right-24: Quick Start](quickstart.md)

-   :material-download:{ .lg .middle } **Installation**

    ---

    Deploy with Docker, Kubernetes, or install from source.

    [:octicons-arrow-right-24: Installation](installation.md)

-   :material-database-search:{ .lg .middle } **First Query**

    ---

    Run your first query through the semantic API.

    [:octicons-arrow-right-24: First Query](first-query.md)

-   :material-chart-box:{ .lg .middle } **Connect BI Tool**

    ---

    Connect Power BI, Tableau, or any BI tool.

    [:octicons-arrow-right-24: Connect BI Tool](connect-bi-tool.md)

</div>

---

## The 5-Step Journey

```mermaid
graph LR
    A[1. Install] --> B[2. Add Source]
    B --> C[3. Define Dataset]
    C --> D[4. Create API Key]
    D --> E[5. Connect BI]
    
    style A fill:#4f46e5,color:#fff
    style B fill:#4f46e5,color:#fff
    style C fill:#4f46e5,color:#fff
    style D fill:#4f46e5,color:#fff
    style E fill:#4f46e5,color:#fff
```

| Step | What You'll Do | Time |
|------|----------------|------|
| 1. Install | Start the connector with Docker | 2 min |
| 2. Add Source | Register your database connection | 2 min |
| 3. Define Dataset | Create your semantic model | 5 min |
| 4. Create API Key | Set up secure access | 1 min |
| 5. Connect BI | Connect Power BI or Tableau | 5 min |

---

## What You'll Achieve

By the end of this guide, you will have:

- [x] A running SetuPranali instance
- [x] A secure connection to your data warehouse
- [x] A semantic dataset with dimensions and metrics
- [x] API key authentication with row-level security
- [x] A working connection in your BI tool

---

## Need Help?

<div class="grid cards" markdown>

-   :material-help-circle:{ .lg .middle } **Troubleshooting**

    ---

    Common issues and how to fix them.

    [:octicons-arrow-right-24: Troubleshooting](../guides/index.md#troubleshooting)

-   :material-message:{ .lg .middle } **Community**

    ---

    Join our community for help and discussion.

    [:octicons-arrow-right-24: GitHub Discussions](https://github.com/setupranali/setupranali.github.io/discussions)

</div>

