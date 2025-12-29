# Production Checklist

Verify your deployment is production-ready.

---

## Security

### Encryption

- [ ] `UBI_SECRET_KEY` is set and secure
- [ ] Key is generated with cryptographic randomness
- [ ] Key is stored securely (secrets manager)

### TLS

- [ ] HTTPS enabled
- [ ] TLS 1.2 or higher
- [ ] Valid SSL certificate
- [ ] HTTP redirects to HTTPS

### API Keys

- [ ] Admin keys are restricted
- [ ] Per-tenant keys created
- [ ] Keys stored securely
- [ ] Key rotation plan in place

### Network

- [ ] Firewall rules configured
- [ ] Database not publicly accessible
- [ ] VPN/private network for sensitive connections
- [ ] IP allowlisting (if applicable)

---

## Performance

### Caching

- [ ] Redis is running
- [ ] `REDIS_URL` is configured
- [ ] `CACHE_TTL_SECONDS` is appropriate
- [ ] Redis has sufficient memory

### Rate Limiting

- [ ] `RATE_LIMIT_QUERY` is configured
- [ ] Limits are appropriate for expected load
- [ ] Redis is available for rate limiting

### Query Guards

- [ ] `MAX_ROWS` is set
- [ ] `MAX_DIMENSIONS` is set
- [ ] `QUERY_TIMEOUT_SECONDS` is set
- [ ] Guards protect against abuse

---

## High Availability

### Replicas

- [ ] Multiple instances deployed
- [ ] Load balancer configured
- [ ] Health checks enabled
- [ ] Graceful shutdown configured

### Database

- [ ] Connection pooling enabled
- [ ] Timeout settings appropriate
- [ ] Reconnection logic works

### Redis

- [ ] Redis is highly available (Sentinel/Cluster)
- [ ] Persistence enabled (AOF/RDB)
- [ ] Memory limits configured

---

## Monitoring

### Health Checks

- [ ] `/health` endpoint accessible
- [ ] Health checks configured in orchestrator
- [ ] Alerts for health failures

### Logging

- [ ] Structured logging enabled
- [ ] Log aggregation configured
- [ ] Log retention policy set

### Metrics

- [ ] Response times tracked
- [ ] Error rates monitored
- [ ] Cache hit rates visible
- [ ] Rate limit hits tracked

### Alerting

- [ ] Alerts for errors
- [ ] Alerts for latency
- [ ] Alerts for resource usage
- [ ] On-call rotation defined

---

## Data Sources

### Connections

- [ ] All sources registered
- [ ] Connections tested
- [ ] Credentials encrypted
- [ ] Service accounts have minimal permissions

### Datasets

- [ ] All datasets defined
- [ ] RLS configured where needed
- [ ] Incremental refresh configured
- [ ] Tested with sample queries

---

## Documentation

### Internal

- [ ] Runbook created
- [ ] Troubleshooting guide
- [ ] Architecture documented
- [ ] Contact information

### External

- [ ] User documentation
- [ ] API documentation
- [ ] Connection guides for BI tools
- [ ] FAQ

---

## Backup & Recovery

### Data

- [ ] Source credentials backed up
- [ ] Configuration backed up
- [ ] Recovery process tested

### Disaster Recovery

- [ ] RTO defined
- [ ] RPO defined
- [ ] Recovery plan documented
- [ ] Recovery tested

---

## Compliance

### Data Protection

- [ ] RLS enforces tenant isolation
- [ ] Audit logging enabled
- [ ] Data retention policy
- [ ] Privacy policy updated

### Access Control

- [ ] Least privilege principle
- [ ] Regular access reviews
- [ ] Key rotation schedule
- [ ] Offboarding process

---

## Launch Verification

### Functional

```bash
# Health check
curl https://bi-api.example.com/health

# Query test
curl -X POST https://bi-api.example.com/v1/query \
  -H "X-API-Key: test-key" \
  -d '{"dataset":"sales","metrics":["revenue"]}'

# OData test
curl https://bi-api.example.com/odata/sales \
  -H "X-API-Key: test-key"
```

### Load Test

```bash
# Simple load test
for i in {1..100}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    https://bi-api.example.com/health &
done
wait
```

### RLS Verification

```bash
# Verify tenant A sees only their data
curl -X POST https://bi-api.example.com/v1/query \
  -H "X-API-Key: pk_tenant_a" \
  -d '{"dataset":"sales","dimensions":["tenant_id"],"metrics":["count"]}'

# Verify tenant B sees only their data
curl -X POST https://bi-api.example.com/v1/query \
  -H "X-API-Key: pk_tenant_b" \
  -d '{"dataset":"sales","dimensions":["tenant_id"],"metrics":["count"]}'
```

---

## Go-Live

- [ ] All checklist items verified
- [ ] Stakeholders notified
- [ ] Support team briefed
- [ ] Monitoring dashboards ready
- [ ] Rollback plan prepared

---

## Post-Launch

- [ ] Monitor error rates
- [ ] Monitor latency
- [ ] Gather user feedback
- [ ] Document lessons learned
- [ ] Plan improvements

