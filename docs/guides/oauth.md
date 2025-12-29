# OAuth 2.0 / OIDC Authentication

Configure OAuth 2.0 and OpenID Connect (OIDC) authentication for SetuPranali.

---

## Overview

SetuPranali supports OAuth 2.0 / OIDC authentication with these providers:

- **Google** - Google Workspace and Cloud Identity
- **Microsoft Azure AD** - Enterprise Azure Active Directory
- **Okta** - Enterprise identity management
- **Auth0** - Identity as a service
- **Keycloak** - Open-source identity management
- **Generic OIDC** - Any OIDC-compliant provider

---

## Quick Start

### 1. Enable OAuth

Set environment variables:

```bash
# Enable OAuth
OAUTH_ENABLED=true

# Configure provider (example: Google)
OAUTH_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=your-client-secret
```

### 2. Use Bearer Token

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

---

## Provider Configuration

### Google

```bash
# Environment variables
OAUTH_ENABLED=true
OAUTH_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=your-client-secret  # Optional for JWT validation

# Optional
OAUTH_DEFAULT_PROVIDER=google
```

**Google Cloud Console Setup:**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Navigate to **APIs & Services** > **Credentials**
4. Create **OAuth 2.0 Client ID**
5. Configure authorized origins and redirect URIs

---

### Microsoft Azure AD

```bash
# Environment variables
OAUTH_ENABLED=true
OAUTH_AZURE_TENANT_ID=your-tenant-id
OAUTH_AZURE_CLIENT_ID=your-client-id
OAUTH_AZURE_CLIENT_SECRET=your-client-secret  # Optional

# Optional
OAUTH_DEFAULT_PROVIDER=azure
```

**Azure Portal Setup:**

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Create new registration
4. Configure **API permissions**
5. Add **Redirect URIs**

**Multi-tenant:**

```bash
# Use 'common' for multi-tenant
OAUTH_AZURE_TENANT_ID=common
```

---

### Okta

```bash
# Environment variables
OAUTH_ENABLED=true
OAUTH_OKTA_DOMAIN=your-domain.okta.com
OAUTH_OKTA_CLIENT_ID=your-client-id
OAUTH_OKTA_CLIENT_SECRET=your-client-secret  # Optional
OAUTH_OKTA_AUDIENCE=api://default

# Optional
OAUTH_DEFAULT_PROVIDER=okta
```

**Okta Admin Setup:**

1. Go to Okta Admin Console
2. Navigate to **Applications** > **Create App Integration**
3. Select **OIDC** and **Web Application**
4. Configure redirect URIs
5. Note the Client ID

---

### Auth0

```bash
# Environment variables
OAUTH_ENABLED=true
OAUTH_AUTH0_DOMAIN=your-tenant.auth0.com
OAUTH_AUTH0_CLIENT_ID=your-client-id
OAUTH_AUTH0_CLIENT_SECRET=your-client-secret  # Optional
OAUTH_AUTH0_AUDIENCE=https://api.yourapp.com

# Optional
OAUTH_DEFAULT_PROVIDER=auth0
```

**Auth0 Dashboard Setup:**

1. Go to [Auth0 Dashboard](https://manage.auth0.com)
2. Create new **Application**
3. Create new **API**
4. Configure allowed origins

---

### Keycloak

```bash
# Environment variables
OAUTH_ENABLED=true
OAUTH_KEYCLOAK_URL=https://keycloak.yourcompany.com
OAUTH_KEYCLOAK_REALM=your-realm
OAUTH_KEYCLOAK_CLIENT_ID=your-client-id
OAUTH_KEYCLOAK_CLIENT_SECRET=your-client-secret  # Optional

# Optional
OAUTH_DEFAULT_PROVIDER=keycloak
```

**Keycloak Admin Setup:**

1. Create new Realm (or use existing)
2. Create new Client
3. Set **Access Type** to `confidential` or `public`
4. Configure **Valid Redirect URIs**

---

### Generic OIDC

```bash
# Environment variables
OAUTH_ENABLED=true
OAUTH_OIDC_ISSUER=https://your-provider.com
OAUTH_OIDC_CLIENT_ID=your-client-id
OAUTH_OIDC_CLIENT_SECRET=your-client-secret
OAUTH_OIDC_AUDIENCE=your-audience
OAUTH_OIDC_DISCOVERY_URL=https://your-provider.com/.well-known/openid-configuration

# Optional
OAUTH_DEFAULT_PROVIDER=oidc
```

---

## Multiple Providers

Configure multiple providers simultaneously:

```bash
OAUTH_ENABLED=true

# Google
OAUTH_GOOGLE_CLIENT_ID=google-client-id

# Azure AD
OAUTH_AZURE_TENANT_ID=azure-tenant-id
OAUTH_AZURE_CLIENT_ID=azure-client-id

# Default provider
OAUTH_DEFAULT_PROVIDER=azure
```

Specify provider in request:

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "X-OAuth-Provider: google" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

---

## Token Claims Mapping

### Tenant Mapping

Map OAuth claims to tenants for RLS:

```bash
# Default claim name
OAUTH_TENANT_CLAIM=tenant_id

# Or use organization/group claim
OAUTH_TENANT_CLAIM=org_id
```

**Token example:**

```json
{
  "sub": "user123",
  "email": "user@company.com",
  "tenant_id": "company-123",
  "roles": ["analyst", "viewer"]
}
```

### Role Mapping

```bash
# Default claim name
OAUTH_ROLES_CLAIM=roles

# Azure AD uses 'roles'
# Keycloak uses 'realm_access.roles'
```

---

## API Key Fallback

Allow API key authentication when OAuth is enabled:

```bash
# Enable both OAuth and API keys (default)
OAUTH_ALLOW_API_KEYS=true

# OAuth only
OAUTH_ALLOW_API_KEYS=false
```

**Request precedence:**

1. Bearer token (OAuth) - if present
2. X-API-Key header - if OAuth fails or not present
3. api_key query parameter - last resort

---

## Helm Configuration

```yaml
# values.yaml
oauth:
  enabled: true
  
  providers:
    google:
      clientId: "your-client-id"
      clientSecret: "your-client-secret"  # From secret
    
    azure:
      tenantId: "your-tenant-id"
      clientId: "your-client-id"
  
  defaultProvider: "azure"
  allowApiKeys: true
  
  # Claims mapping
  tenantClaim: "tenant_id"
  rolesClaim: "roles"
```

**Using secrets:**

```yaml
# values.yaml
oauth:
  enabled: true
  existingSecret: "oauth-secrets"
```

```yaml
# oauth-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: oauth-secrets
type: Opaque
stringData:
  OAUTH_GOOGLE_CLIENT_SECRET: "secret-value"
  OAUTH_AZURE_CLIENT_SECRET: "secret-value"
```

---

## Docker Configuration

```yaml
# docker-compose.yml
services:
  setupranali:
    image: adeygifting/connector
    environment:
      - OAUTH_ENABLED=true
      - OAUTH_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - OAUTH_GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - OAUTH_ALLOW_API_KEYS=true
```

---

## Token Validation

### JWT Validation

SetuPranali validates:

- **Signature** - Using provider's JWKS
- **Expiration** - `exp` claim
- **Audience** - `aud` claim (if configured)
- **Issuer** - `iss` claim

### JWKS Caching

JWKS are cached to improve performance:

```bash
# Cache TTL (default: 1 hour)
OAUTH_JWKS_CACHE_TTL=3600
```

### Leeway

Allow clock skew between servers:

```bash
# Leeway in seconds (default: 60)
OAUTH_LEEWAY=60
```

---

## Row-Level Security

OAuth tokens can provide tenant context for RLS:

```yaml
# catalog.yaml
datasets:
  - id: orders
    rls:
      mode: tenant_column
      field: tenant_id
```

The `tenant_id` from the OAuth token is automatically used for filtering.

---

## Examples

### Python SDK

```python
from setupranali import SetuPranaliClient

# Using OAuth token
client = SetuPranaliClient(
    url="https://your-server.com",
    token="eyJhbGciOiJSUzI1NiIs..."  # OAuth token instead of api_key
)

df = client.query(
    dataset="orders",
    dimensions=["region"],
    metrics=["revenue"]
)
```

### JavaScript SDK

```typescript
import { SetuPranali } from '@setupranali/sdk';

const client = new SetuPranali({
  url: 'https://your-server.com',
  token: 'eyJhbGciOiJSUzI1NiIs...'  // OAuth token
});

const data = await client.query({
  dataset: 'orders',
  dimensions: ['region'],
  metrics: ['revenue']
});
```

### cURL

```bash
# Get token from OAuth provider
TOKEN=$(curl -s -X POST https://oauth.provider.com/token \
  -d "grant_type=client_credentials" \
  -d "client_id=your-client-id" \
  -d "client_secret=your-client-secret" \
  | jq -r '.access_token')

# Query SetuPranali
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

---

## Troubleshooting

### Invalid Token

```
401 Unauthorized: Invalid token
```

**Solutions:**

1. Verify token hasn't expired
2. Check token is from correct provider
3. Verify audience matches configuration
4. Check issuer matches configuration

### Token Expired

```
401 Unauthorized: Token has expired
```

**Solutions:**

1. Refresh the token
2. Check system clock synchronization
3. Increase `OAUTH_LEEWAY` for clock skew

### JWKS Fetch Failed

```
500 Internal Server Error: Failed to fetch signing keys
```

**Solutions:**

1. Verify provider URL is accessible
2. Check firewall/network settings
3. Verify JWKS URI is correct

### Audience Mismatch

```
401 Unauthorized: Invalid token audience
```

**Solutions:**

1. Verify `OAUTH_*_AUDIENCE` is correct
2. Check token's `aud` claim
3. Disable audience verification if not needed:
   ```bash
   OAUTH_VERIFY_AUD=false
   ```

---

## Security Best Practices

1. **Use HTTPS** - Always use HTTPS in production
2. **Short token lifetime** - Use short-lived access tokens
3. **Validate audience** - Always validate the `aud` claim
4. **Rotate secrets** - Regularly rotate client secrets
5. **Least privilege** - Grant minimal required scopes
6. **Monitor logs** - Watch for authentication failures

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `OAUTH_ENABLED` | Enable OAuth authentication | `false` |
| `OAUTH_DEFAULT_PROVIDER` | Default provider name | (first configured) |
| `OAUTH_ALLOW_API_KEYS` | Allow API key fallback | `true` |
| `OAUTH_TENANT_CLAIM` | Claim for tenant ID | `tenant_id` |
| `OAUTH_ROLES_CLAIM` | Claim for user roles | `roles` |
| `OAUTH_LEEWAY` | Clock skew tolerance (seconds) | `60` |
| `OAUTH_JWKS_CACHE_TTL` | JWKS cache TTL (seconds) | `3600` |
| `OAUTH_VERIFY_AUD` | Verify audience claim | `true` |
| `OAUTH_GOOGLE_CLIENT_ID` | Google client ID | - |
| `OAUTH_GOOGLE_CLIENT_SECRET` | Google client secret | - |
| `OAUTH_AZURE_TENANT_ID` | Azure AD tenant ID | `common` |
| `OAUTH_AZURE_CLIENT_ID` | Azure AD client ID | - |
| `OAUTH_AZURE_CLIENT_SECRET` | Azure AD client secret | - |
| `OAUTH_OKTA_DOMAIN` | Okta domain | - |
| `OAUTH_OKTA_CLIENT_ID` | Okta client ID | - |
| `OAUTH_OKTA_AUDIENCE` | Okta audience | `api://default` |
| `OAUTH_AUTH0_DOMAIN` | Auth0 domain | - |
| `OAUTH_AUTH0_CLIENT_ID` | Auth0 client ID | - |
| `OAUTH_AUTH0_AUDIENCE` | Auth0 audience | - |
| `OAUTH_KEYCLOAK_URL` | Keycloak URL | - |
| `OAUTH_KEYCLOAK_REALM` | Keycloak realm | `master` |
| `OAUTH_KEYCLOAK_CLIENT_ID` | Keycloak client ID | - |
| `OAUTH_OIDC_ISSUER` | Generic OIDC issuer | - |
| `OAUTH_OIDC_CLIENT_ID` | Generic OIDC client ID | - |
| `OAUTH_OIDC_DISCOVERY_URL` | OIDC discovery URL | - |

