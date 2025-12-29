# Enterprise Setup Example

Production-ready configuration for enterprise deployment.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Load Balancer   │
                    │   (HTTPS/TLS)     │
                    └─────────┬─────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
     ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
     │Connector 1│      │Connector 2│      │Connector 3│
     └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Redis Cluster   │
                    │   (HA/Sentinel)   │
                    └───────────────────┘
```

---

## Kubernetes Deployment

### values.yaml

```yaml
# Helm values for enterprise deployment

replicaCount: 3

image:
  repository: adeygifting/connector
  tag: "1.0.0"
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilization: 70

redis:
  enabled: true
  architecture: replication
  auth:
    enabled: true
    password: "${REDIS_PASSWORD}"

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: bi-api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: bi-api-tls
      hosts:
        - bi-api.example.com

config:
  cacheTtl: 300
  rateLimitQuery: "200/minute"
  rateLimitOdata: "100/minute"
  maxRows: 500000
  maxDimensions: 15
  queryTimeout: 60

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true

podDisruptionBudget:
  enabled: true
  minAvailable: 2

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: ubi-connector
          topologyKey: kubernetes.io/hostname
```

---

## Secrets Management

### External Secrets

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ubi-secrets
spec:
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: ubi-secrets
  data:
    - secretKey: secret-key
      remoteRef:
        key: ubi-connector/production
        property: secret_key
    - secretKey: snowflake-password
      remoteRef:
        key: ubi-connector/production
        property: snowflake_password
```

---

## Multi-Tenant Configuration

### API Keys

```yaml
api_keys:
  # Platform admin
  - key: "${ADMIN_KEY}"
    role: admin
    description: "Platform operations"
  
  # Enterprise customers
  - key: "${ACME_KEY}"
    tenant: acme_corp
    role: analyst
    rate_limit: "500/minute"
  
  - key: "${GLOBEX_KEY}"
    tenant: globex_inc
    role: analyst
    rate_limit: "500/minute"
  
  # Standard customers
  - key: "${STARTUP_KEY}"
    tenant: startup_io
    role: analyst
    rate_limit: "100/minute"
```

### catalog.yaml

```yaml
datasets:
  - name: sales
    source: snowflake-prod
    table: ANALYTICS.FACT_SALES
    
    dimensions:
      - name: region
        type: string
        expr: REGION_NAME
      - name: product
        type: string
        expr: PRODUCT_CATEGORY
      - name: sale_date
        type: date
        expr: SALE_DATE
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(SALE_AMOUNT)"
      - name: orders
        type: number
        expr: "COUNT(*)"
      - name: avg_order_value
        type: number
        expr: "AVG(SALE_AMOUNT)"
    
    rls:
      tenant_column: TENANT_ID
    
    incremental:
      date_column: SALE_DATE
      min_date: "2020-01-01"
```

---

## Monitoring

### Prometheus Alerts

```yaml
groups:
  - name: ubi-connector
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on BI Connector"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on BI Connector"
      
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
```

### Grafana Dashboard

```json
{
  "title": "SetuPranali",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total{status=~'5..'}[5m])"
        }
      ]
    },
    {
      "title": "Cache Hit Rate",
      "type": "gauge",
      "targets": [
        {
          "expr": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))"
        }
      ]
    }
  ]
}
```

---

## Security Hardening

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ubi-connector
spec:
  podSelector:
    matchLabels:
      app: ubi-connector
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: redis
      ports:
        - port: 6379
    - to:
        - ipBlock:
            cidr: 10.0.0.0/8  # Internal databases
      ports:
        - port: 5432
        - port: 443
```

### Pod Security

```yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
    - name: connector
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
```

---

## Disaster Recovery

### Backup Script

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/ubi-connector/$DATE"

mkdir -p $BACKUP_DIR

# Backup configuration
kubectl get configmap ubi-config -o yaml > $BACKUP_DIR/configmap.yaml
kubectl get secret ubi-secrets -o yaml > $BACKUP_DIR/secrets.yaml

# Backup Redis data
kubectl exec -it redis-0 -- redis-cli BGSAVE
kubectl cp redis-0:/data/dump.rdb $BACKUP_DIR/redis.rdb

# Upload to S3
aws s3 sync $BACKUP_DIR s3://backups/ubi-connector/$DATE/
```

### Recovery Procedure

1. Deploy fresh cluster
2. Restore secrets
3. Restore ConfigMap
4. Restore Redis data
5. Verify health
6. Update DNS

