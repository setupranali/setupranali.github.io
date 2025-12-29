# Kubernetes Deployment

Deploy SetuPranali on Kubernetes.

---

## Quick Start with Helm

```bash
# Add repository
helm repo add setupranali https://charts.setupranali.io
helm repo update

# Install
helm install ubi-connector setupranali/connector \
  --set secretKey=$(openssl rand -base64 32)
```

---

## Manual Deployment

### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: setupranali
```

### Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ubi-secrets
  namespace: setupranali
type: Opaque
stringData:
  secret-key: "your-secret-key-here"
```

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ubi-config
  namespace: setupranali
data:
  catalog.yaml: |
    datasets:
      - name: sales
        source: postgres-prod
        table: sales
        dimensions:
          - name: region
            type: string
        metrics:
          - name: revenue
            type: number
            expr: "SUM(amount)"
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ubi-connector
  namespace: setupranali
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ubi-connector
  template:
    metadata:
      labels:
        app: ubi-connector
    spec:
      containers:
        - name: connector
          image: setupranali/connector:latest
          ports:
            - containerPort: 8080
          env:
            - name: UBI_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: ubi-secrets
                  key: secret-key
            - name: REDIS_URL
              value: "redis://redis:6379"
            - name: CACHE_TTL_SECONDS
              value: "300"
          volumeMounts:
            - name: catalog
              mountPath: /app/catalog.yaml
              subPath: catalog.yaml
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: catalog
          configMap:
            name: ubi-config
```

### Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ubi-connector
  namespace: setupranali
spec:
  selector:
    app: ubi-connector
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ubi-connector
  namespace: setupranali
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - bi-api.example.com
      secretName: ubi-tls
  rules:
    - host: bi-api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ubi-connector
                port:
                  number: 80
```

---

## Redis Deployment

```yaml
# redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: setupranali
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: setupranali
spec:
  selector:
    app: redis
  ports:
    - port: 6379
```

---

## Apply Manifests

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f redis.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
```

---

## Helm Values

```yaml
# values.yaml
replicaCount: 3

image:
  repository: setupranali/connector
  tag: latest

secretKey: ""  # Set via --set or external secret

redis:
  enabled: true
  url: redis://redis:6379

config:
  cacheTtl: 300
  rateLimitQuery: "100/minute"
  maxRows: 100000

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

ingress:
  enabled: true
  host: bi-api.example.com
  tls: true

catalog: |
  datasets:
    - name: sales
      source: postgres-prod
      table: sales
```

Install with values:

```bash
helm install ubi-connector setupranali/connector -f values.yaml
```

---

## Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ubi-connector
  namespace: setupranali
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ubi-connector
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## Monitoring

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ubi-connector
  namespace: setupranali
spec:
  selector:
    matchLabels:
      app: ubi-connector
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

---

## Troubleshooting

### Check Pods

```bash
kubectl get pods -n setupranali
kubectl describe pod <pod-name> -n setupranali
```

### View Logs

```bash
kubectl logs -l app=ubi-connector -n setupranali -f
```

### Shell Access

```bash
kubectl exec -it <pod-name> -n setupranali -- /bin/sh
```

