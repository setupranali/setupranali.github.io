# Helm Chart Deployment

Deploy SetuPranali to Kubernetes using the official Helm chart.

---

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2+
- kubectl configured for your cluster

---

## Quick Start

=== "Helm Repository"

    ```bash
    # Add the repository
    helm repo add setupranali https://setupranali.github.io/charts
    helm repo update
    
    # Install
    helm install setupranali setupranali/setupranali \
      --namespace setupranali \
      --create-namespace
    ```

=== "From Source"

    ```bash
    cd helm/setupranali
    helm dependency update
    helm install setupranali . \
      --namespace setupranali \
      --create-namespace
    ```

---

## Verify Installation

```bash
# Check pods
kubectl get pods -n setupranali

# Port-forward to test
kubectl port-forward -n setupranali svc/setupranali 8080:8080

# Test health
curl http://localhost:8080/v1/health
```

---

## Configuration

### Essential Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `secrets.encryptionKey` | Fernet encryption key | Auto-generated |
| `redis.enabled` | Deploy bundled Redis | `true` |
| `ingress.enabled` | Enable ingress | `false` |

### Image Configuration

```yaml
image:
  repository: adeygifting/connector
  pullPolicy: IfNotPresent
  tag: ""  # Defaults to Chart appVersion
```

### Secrets

```yaml
secrets:
  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  encryptionKey: "your-fernet-key-here"
  
  # Or use existing secret
  existingSecret: "my-secret"
  existingSecretKeys:
    encryptionKey: "UBI_SECRET_KEY"
```

!!! warning "Production Encryption Key"
    Always set a stable `encryptionKey` in production. Auto-generated keys change on upgrade, making encrypted credentials unusable.

### Redis

=== "Bundled Redis"

    ```yaml
    redis:
      enabled: true
      architecture: standalone  # or replication
      auth:
        enabled: false
      master:
        persistence:
          enabled: false  # Enable for persistence
          size: 1Gi
    ```

=== "External Redis"

    ```yaml
    redis:
      enabled: false
    
    externalRedis:
      host: redis.example.com
      port: 6379
      password: ""
      existingSecret: redis-credentials
      existingSecretKey: password
    ```

### Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: bi-api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: setupranali-tls
      hosts:
        - bi-api.example.com
```

### Autoscaling

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80
```

### Resources

```yaml
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 256Mi
```

---

## Catalog Configuration

### Inline Catalog

```yaml
catalog:
  content: |
    datasets:
      - id: orders
        name: Orders
        source: my-warehouse
        table: fact_orders
        dimensions:
          - name: city
            expr: city_name
        metrics:
          - name: revenue
            expr: "SUM(amount)"
        rls:
          mode: tenant_column
          field: tenant_id
```

### External ConfigMap

```yaml
catalog:
  existingConfigMap: my-catalog-configmap
```

Create the ConfigMap:

```bash
kubectl create configmap my-catalog-configmap \
  --from-file=catalog.yaml=./catalog.yaml \
  -n setupranali
```

---

## Production Deployment

### 1. Create Namespace

```bash
kubectl create namespace setupranali
```

### 2. Create Secrets

```bash
# Generate encryption key
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create secret
kubectl create secret generic setupranali-secrets \
  --namespace setupranali \
  --from-literal=UBI_SECRET_KEY="$ENCRYPTION_KEY"
```

### 3. Create values file

```yaml
# production-values.yaml
replicaCount: 3

secrets:
  existingSecret: setupranali-secrets

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: bi-api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: setupranali-tls
      hosts:
        - bi-api.example.com

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

redis:
  enabled: true
  architecture: replication
  auth:
    enabled: true
    password: "strong-redis-password"
  master:
    persistence:
      enabled: true
      size: 5Gi
```

### 4. Install

```bash
helm install setupranali setupranali/setupranali \
  --namespace setupranali \
  --values production-values.yaml
```

---

## Upgrading

```bash
# Update repository
helm repo update

# Upgrade release
helm upgrade setupranali setupranali/setupranali \
  --namespace setupranali \
  --values production-values.yaml
```

---

## Monitoring

### Prometheus Metrics

Add annotations to scrape metrics:

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

### Health Checks

The chart configures liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /v1/health
    port: http
  initialDelaySeconds: 10
  periodSeconds: 15

readinessProbe:
  httpGet:
    path: /v1/health
    port: http
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## Troubleshooting

### View Logs

```bash
kubectl logs -n setupranali -l app.kubernetes.io/name=setupranali -f
```

### Check Events

```bash
kubectl get events -n setupranali --sort-by='.lastTimestamp'
```

### Debug Pod

```bash
kubectl exec -it -n setupranali <pod-name> -- /bin/sh
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Pods not starting | Check `kubectl describe pod` for events |
| Redis connection failed | Verify Redis is running: `kubectl get pods -l app.kubernetes.io/name=redis` |
| Ingress not working | Check ingress controller logs and TLS secret |
| Encryption errors | Ensure encryption key hasn't changed between upgrades |

---

## Uninstall

```bash
# Uninstall release
helm uninstall setupranali -n setupranali

# Delete namespace (optional)
kubectl delete namespace setupranali
```

---

## Chart Values Reference

See the full [values.yaml](https://github.com/setupranali/setupranali.github.io/blob/main/helm/setupranali/values.yaml) for all configuration options.

