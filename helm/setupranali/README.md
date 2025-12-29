# SetuPranali Helm Chart

Deploy SetuPranali to Kubernetes with ease.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2+
- PV provisioner (for Redis persistence, optional)

## Installation

### Add the Helm Repository

```bash
# Add the SetuPranali Helm repository
helm repo add setupranali https://setupranali.github.io/charts
helm repo update
```

### Quick Start

```bash
# Install with default values
helm install my-setupranali setupranali/setupranali

# Install with custom values
helm install my-setupranali setupranali/setupranali \
  --set secrets.encryptionKey="your-fernet-key" \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=bi-api.example.com
```

### Install from Source

```bash
cd helm/setupranali
helm dependency update
helm install my-setupranali .
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `adeygifting/connector` |
| `image.tag` | Image tag | `Chart.appVersion` |
| `secrets.encryptionKey` | Fernet encryption key | Auto-generated |
| `redis.enabled` | Deploy bundled Redis | `true` |
| `ingress.enabled` | Enable ingress | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |

### Full Values Reference

See [values.yaml](values.yaml) for all configuration options.

## Examples

### Basic Installation

```bash
helm install setupranali setupranali/setupranali \
  --namespace setupranali \
  --create-namespace
```

### Production Installation

```bash
# Create namespace
kubectl create namespace setupranali

# Create secrets
kubectl create secret generic setupranali-secrets \
  --namespace setupranali \
  --from-literal=UBI_SECRET_KEY="your-fernet-key"

# Install with production values
helm install setupranali setupranali/setupranali \
  --namespace setupranali \
  --values production-values.yaml
```

Example `production-values.yaml`:

```yaml
replicaCount: 3

secrets:
  existingSecret: setupranali-secrets

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

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

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
    password: "redis-password"
  master:
    persistence:
      enabled: true
      size: 5Gi
```

### With External Redis

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

### Custom Catalog

```yaml
catalog:
  content: |
    datasets:
      - id: orders
        name: Orders
        description: Order transactions
        source: my-warehouse
        table: fact_orders
        dimensions:
          - name: city
            expr: city_name
          - name: region
            expr: region_name
        metrics:
          - name: revenue
            expr: "SUM(amount)"
          - name: orders
            expr: "COUNT(*)"
        rls:
          mode: tenant_column
          field: tenant_id
```

### Using Existing ConfigMap

```yaml
catalog:
  existingConfigMap: my-catalog-configmap
```

## Upgrading

```bash
# Update repository
helm repo update

# Upgrade release
helm upgrade my-setupranali setupranali/setupranali
```

### From 1.0.x to 1.1.x

No breaking changes. Standard upgrade process.

## Uninstallation

```bash
helm uninstall my-setupranali
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Ingress                              │
│                    (optional, HTTPS)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        Service                              │
│                    (ClusterIP:8080)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Deployment                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Pod 1      │ │  Pod 2      │ │  Pod N      │           │
│  │  (replica)  │ │  (replica)  │ │  (replica)  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Redis (Cache)                           │
│                  (bundled or external)                      │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=setupranali

# Check pod events
kubectl describe pod <pod-name>

# Check logs
kubectl logs -l app.kubernetes.io/name=setupranali
```

### Connection issues

```bash
# Port-forward to test locally
kubectl port-forward svc/my-setupranali 8080:8080

# Test health endpoint
curl http://localhost:8080/v1/health
```

### Redis connection issues

```bash
# Check Redis pods
kubectl get pods -l app.kubernetes.io/name=redis

# Test Redis connection from setupranali pod
kubectl exec -it <setupranali-pod> -- redis-cli -h <redis-host> ping
```

## Security Considerations

1. **Encryption Key**: Always set a stable `secrets.encryptionKey` in production
2. **TLS**: Enable TLS via ingress in production
3. **Network Policies**: Consider adding NetworkPolicies
4. **Pod Security**: Default security context runs as non-root

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](../../LICENSE) for details.

