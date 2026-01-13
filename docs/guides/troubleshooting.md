# Troubleshooting Guide

Common issues and solutions for SetuPranali.

---

## Quick Diagnostics

### Check System Health

```bash
curl http://localhost:8080/v1/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "cache": {
    "enabled": true,
    "redis_available": true
  }
}
```

### Check Server Logs

```bash
# Docker
docker logs setupranali

# Local
tail -f /tmp/ubi-backend.log
```

---

## Common Issues

### 1. Connection Refused

**Symptoms**: Cannot connect to API

**Solutions**:
- Verify server is running: `ps aux | grep uvicorn`
- Check port is correct: `lsof -i :8080`
- Verify firewall settings
- Check Docker container is running: `docker ps`

### 2. API Key Authentication Failed

**Symptoms**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:
- Verify API key is correct
- Check `X-API-Key` header is present
- Ensure key is not revoked
- Verify key has correct tenant/role

**Test**:
```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "limit": 1}'
```

### 3. Dataset Not Found

**Symptoms**: `404 Dataset 'xyz' not found`

**Solutions**:
- Verify dataset exists in `catalog.yaml`
- Check dataset ID matches exactly
- Reload catalog: Restart server or call `/v1/introspection/datasets`
- Verify catalog file is valid YAML

**Check**:
```bash
curl http://localhost:8080/v1/datasets
```

### 4. Query Execution Timeout

**Symptoms**: Query hangs or times out

**Solutions**:
- Check database connection
- Verify query is not too complex
- Check database performance
- Increase timeout in configuration
- Use LIMIT to reduce result size

**Debug**:
```bash
# Check query in logs
tail -f /tmp/ubi-backend.log | grep "query"
```

### 5. SQL Syntax Error

**Symptoms**: `SQL parsing error` or `Invalid SQL syntax`

**Solutions**:
- Verify SQL syntax is correct
- Check dialect compatibility
- Use semantic queries instead of raw SQL
- Review SQLGlot error message

**Test**:
```bash
# Use SQL validation
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: your-key" \
  -d '{"sql": "SELECT 1", "dataset": "orders"}'
```

### 6. Redis Connection Failed

**Symptoms**: Cache disabled, rate limiting uses fallback

**Solutions**:
- Start Redis: `redis-server` or `docker run -d -p 6379:6379 redis:7-alpine`
- Check Redis URL: `echo $REDIS_URL`
- Verify Redis is accessible: `redis-cli ping`
- System works without Redis (uses in-memory fallback)

### 7. Demo Data Not Available

**Symptoms**: Queries return no data

**Solutions**:
- Verify demo data is seeded (check server startup logs)
- Restart server to re-seed data
- Check database connection
- Verify table exists: `SELECT COUNT(*) FROM orders`

**Re-seed**:
```python
# In Python
from app.adapters.duckdb_adapter import get_shared_duckdb
adapter = get_shared_duckdb()
# Demo data seeds on server startup
```

### 8. Web UI Not Loading

**Symptoms**: Frontend shows errors or blank page

**Solutions**:
- Check frontend is running: `curl http://localhost:5173`
- Verify backend is accessible: `curl http://localhost:8080/v1/health`
- Check browser console (F12) for errors
- Verify API URL in frontend config

**Check**:
```bash
# Frontend
ps aux | grep vite

# Backend
ps aux | grep uvicorn
```

### 9. CORS Errors

**Symptoms**: Browser shows CORS errors in console

**Solutions**:
- Check CORS settings in backend
- Verify frontend URL is in allowed origins
- Check API proxy configuration
- Use same origin for frontend/backend in development

### 10. Rate Limit Exceeded

**Symptoms**: `429 Too Many Requests`

**Solutions**:
- Wait for rate limit window to reset
- Check rate limit configuration
- Use fewer concurrent requests
- Disable rate limiting for development: `RATE_LIMIT_ENABLED=false`

---

## Database-Specific Issues

### PostgreSQL

**Connection Issues**:
- Verify `host`, `port`, `database` are correct
- Check SSL settings match server configuration
- Verify user has necessary permissions
- Check `pg_hba.conf` allows connections

**Query Issues**:
- Check PostgreSQL version compatibility
- Verify table/column names are correct
- Check for schema qualification issues

### Snowflake

**Connection Issues**:
- Verify account URL format: `xxx.snowflakecomputing.com`
- Check warehouse, database, schema are correct
- Verify user has access to warehouse
- Check network connectivity

**Query Issues**:
- Verify warehouse is running
- Check query timeout settings
- Review Snowflake query history

### BigQuery

**Connection Issues**:
- Verify service account key is valid
- Check project ID is correct
- Verify service account has BigQuery permissions
- Check authentication method

**Query Issues**:
- Review BigQuery quotas
- Check dataset location matches
- Verify table names are correct

---

## Performance Issues

### Slow Queries

**Diagnosis**:
1. Check query execution time in response
2. Review database query logs
3. Check for missing indexes
4. Verify query complexity

**Solutions**:
- Add indexes on filtered columns
- Use LIMIT to reduce result size
- Enable query caching
- Optimize query structure

### High Memory Usage

**Diagnosis**:
1. Check server memory: `top` or `htop`
2. Review query result sizes
3. Check cache size

**Solutions**:
- Reduce query limits
- Enable result pagination
- Clear cache if needed
- Increase server memory

### Cache Not Working

**Diagnosis**:
1. Check Redis connection
2. Verify cache is enabled
3. Review cache hit rate

**Solutions**:
- Start Redis server
- Verify `CACHE_ENABLED=true`
- Check cache TTL settings
- Review cache key generation

---

## Debugging Tips

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
python3 -m uvicorn app.main:app --port 8080
```

### Test Individual Components

```python
# Test database connection
from app.adapters.postgres_adapter import PostgresAdapter
adapter = PostgresAdapter(config)
adapter.connect()
result = adapter.execute("SELECT 1")

# Test query engine
from app.query_engine import compile_and_run_query
# ... test query compilation

# Test SQLGlot
from app.sql_builder import SQLBuilder
builder = SQLBuilder(dialect="postgres")
sql, params = builder.build_query(...)
```

### Use API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

---

## Getting Help

### Check Logs

```bash
# Backend logs
tail -f /tmp/ubi-backend.log

# Docker logs
docker logs -f setupranali

# Frontend logs (browser console)
# Press F12 → Console tab
```

### Community Resources

- [GitHub Issues](https://github.com/setupranali/setupranali.github.io/issues)
- [Discord Community](https://discord.gg/setupranali)
- [Documentation](https://setupranali.github.io/)

### Report Issues

When reporting issues, include:

1. **Error Message** - Full error text
2. **Steps to Reproduce** - What you did
3. **Expected Behavior** - What should happen
4. **Actual Behavior** - What actually happened
5. **Environment** - OS, Python version, database type
6. **Logs** - Relevant log excerpts

---

## Next Steps

- [Configuration Guide](../deployment/configuration.md)
- [Production Checklist](../deployment/production-checklist.md)
- [API Reference](../api-reference/index.md)

