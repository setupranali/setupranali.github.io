# Guides

Practical guides for common tasks and configurations.

---

## Quick Links

<div class="grid cards" markdown>

-   :material-database:{ .lg .middle } **Defining Datasets**

    ---

    Create and configure your semantic datasets.

    [:octicons-arrow-right-24: Datasets](datasets.md)

-   :material-shield-lock:{ .lg .middle } **Row-Level Security**

    ---

    Implement per-tenant data isolation.

    [:octicons-arrow-right-24: RLS](rls.md)

-   :material-refresh:{ .lg .middle } **Incremental Refresh**

    ---

    Efficient data loading for BI tools.

    [:octicons-arrow-right-24: Incremental Refresh](incremental-refresh.md)

-   :material-account-group:{ .lg .middle } **Multi-Tenant Setup**

    ---

    Configure for multiple customers.

    [:octicons-arrow-right-24: Multi-Tenant](multi-tenant.md)

-   :material-key:{ .lg .middle } **API Keys**

    ---

    Create and manage API keys.

    [:octicons-arrow-right-24: API Keys](api-keys.md)

</div>

---

## Getting Help

If you don't find what you're looking for:

- Check the [API Reference](../api-reference/index.md)
- Review [Concepts](../concepts/index.md)
- Ask in [GitHub Discussions](https://github.com/setupranali/setupranali.github.io/discussions)

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check API key in X-API-Key header |
| 404 Dataset Not Found | Verify dataset name in catalog.yaml |
| Empty Results | Check RLS configuration |
| Slow Queries | Enable caching, check indexes |
| Rate Limited | Reduce request frequency or increase limit |

### Logs

```bash
# Docker
docker logs ubi-connector

# Kubernetes
kubectl logs -l app=ubi-connector

# Local
# Logs print to stdout by default
```

### Health Check

```bash
curl http://localhost:8080/health
```

Expected:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "redis": "connected"
}
```

