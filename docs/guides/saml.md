# SAML 2.0 SSO Authentication

Configure SAML 2.0 Single Sign-On (SSO) for enterprise identity provider integration.

---

## Overview

SetuPranali supports SAML 2.0 SSO with enterprise identity providers:

- **Okta** - Enterprise identity management
- **Microsoft Azure AD** - Azure Active Directory (SAML mode)
- **Microsoft ADFS** - Active Directory Federation Services
- **OneLogin** - Cloud identity provider
- **PingFederate** - Enterprise federation
- **Google Workspace** - Google SAML apps
- **Shibboleth** - Open-source IdP
- **Generic SAML 2.0** - Any SAML 2.0 compliant IdP

---

## Prerequisites

Install the SAML library:

```bash
pip install python3-saml
```

---

## Quick Start

### 1. Configure Service Provider

```bash
# Enable SAML
SAML_ENABLED=true

# Service Provider (SetuPranali)
SAML_SP_ENTITY_ID=https://your-app.com/saml/metadata
SAML_SP_ACS_URL=https://your-app.com/saml/acs
```

### 2. Configure Identity Provider

```bash
# Identity Provider
SAML_IDP_NAME=okta
SAML_IDP_ENTITY_ID=http://www.okta.com/exk123
SAML_IDP_SSO_URL=https://your-domain.okta.com/app/exk123/sso/saml
SAML_IDP_CERT="-----BEGIN CERTIFICATE-----
MIIDpDCCAo...
-----END CERTIFICATE-----"
```

### 3. Initiate Login

```bash
# Redirect to IdP
curl -L http://localhost:8080/saml/login
```

---

## Service Provider Configuration

The Service Provider (SP) is SetuPranali - your application.

### Required Settings

```bash
# Unique identifier for your application
SAML_SP_ENTITY_ID=https://your-app.com/saml/metadata

# Assertion Consumer Service - where IdP sends the response
SAML_SP_ACS_URL=https://your-app.com/saml/acs
```

### Optional Settings

```bash
# Single Logout URL
SAML_SP_SLO_URL=https://your-app.com/saml/slo

# Metadata URL
SAML_SP_METADATA_URL=https://your-app.com/saml/metadata

# SP Certificate and Key (for signing)
SAML_SP_CERT="-----BEGIN CERTIFICATE-----..."
SAML_SP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."

# Security options
SAML_WANT_ASSERTIONS_SIGNED=true
SAML_WANT_ASSERTIONS_ENCRYPTED=false
SAML_AUTHN_REQUESTS_SIGNED=false
```

---

## Identity Provider Configuration

### Okta

```bash
SAML_ENABLED=true
SAML_IDP_NAME=okta
SAML_IDP_ENTITY_ID=http://www.okta.com/exk123abc
SAML_IDP_SSO_URL=https://your-domain.okta.com/app/your-app/exk123abc/sso/saml
SAML_IDP_SLO_URL=https://your-domain.okta.com/app/your-app/exk123abc/slo/saml
SAML_IDP_CERT="..."
```

**Okta Admin Setup:**

1. Go to **Applications** > **Create App Integration**
2. Select **SAML 2.0**
3. Configure:
   - **Single sign-on URL**: `https://your-app.com/saml/acs`
   - **Audience URI (SP Entity ID)**: `https://your-app.com/saml/metadata`
4. Configure Attribute Statements
5. Download IdP certificate

---

### Microsoft Azure AD

```bash
SAML_ENABLED=true
SAML_IDP_NAME=azure
SAML_IDP_ENTITY_ID=https://sts.windows.net/your-tenant-id/
SAML_IDP_SSO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
SAML_IDP_SLO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
SAML_IDP_CERT="..."
```

**Azure Portal Setup:**

1. Go to **Azure Active Directory** > **Enterprise applications**
2. Create **New application** > **Non-gallery application**
3. Configure **Single sign-on** > **SAML**
4. Set:
   - **Identifier (Entity ID)**: `https://your-app.com/saml/metadata`
   - **Reply URL (ACS)**: `https://your-app.com/saml/acs`
5. Download Certificate (Base64)

---

### Microsoft ADFS

```bash
SAML_ENABLED=true
SAML_IDP_NAME=adfs
SAML_IDP_ENTITY_ID=https://adfs.company.com/adfs/services/trust
SAML_IDP_SSO_URL=https://adfs.company.com/adfs/ls/
SAML_IDP_SLO_URL=https://adfs.company.com/adfs/ls/
SAML_IDP_CERT="..."
```

**ADFS Setup:**

1. Open AD FS Management
2. Add **Relying Party Trust**
3. Enter SP metadata URL or configure manually
4. Configure **Claim Rules**
5. Export token signing certificate

---

### OneLogin

```bash
SAML_ENABLED=true
SAML_IDP_NAME=onelogin
SAML_IDP_ENTITY_ID=https://app.onelogin.com/saml/metadata/123456
SAML_IDP_SSO_URL=https://your-company.onelogin.com/trust/saml2/http-post/sso/123456
SAML_IDP_SLO_URL=https://your-company.onelogin.com/trust/saml2/http-redirect/slo/123456
SAML_IDP_CERT="..."
```

---

### Google Workspace

```bash
SAML_ENABLED=true
SAML_IDP_NAME=google
SAML_IDP_ENTITY_ID=https://accounts.google.com/o/saml2?idpid=C01234567
SAML_IDP_SSO_URL=https://accounts.google.com/o/saml2/idp?idpid=C01234567
SAML_IDP_CERT="..."
```

**Google Admin Setup:**

1. Go to **Admin Console** > **Apps** > **Web and mobile apps**
2. Add **Custom SAML app**
3. Configure:
   - **ACS URL**: `https://your-app.com/saml/acs`
   - **Entity ID**: `https://your-app.com/saml/metadata`
4. Add attribute mappings
5. Download IdP metadata

---

## Attribute Mapping

Map SAML attributes to SetuPranali user fields:

```bash
# Standard attributes
SAML_ATTR_EMAIL=email
SAML_ATTR_FIRST_NAME=firstName
SAML_ATTR_LAST_NAME=lastName
SAML_ATTR_DISPLAY_NAME=displayName

# For multi-tenancy
SAML_ATTR_TENANT_ID=tenantId

# For authorization
SAML_ATTR_ROLES=roles
```

### Common Attribute Names by IdP

| Field | Okta | Azure AD | ADFS |
|-------|------|----------|------|
| Email | `email` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | `email` |
| First Name | `firstName` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` | `givenName` |
| Last Name | `lastName` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname` | `sn` |
| Groups | `groups` | `http://schemas.microsoft.com/ws/2008/06/identity/claims/groups` | `groups` |

---

## Session Management

### Session Duration

```bash
# Session TTL in seconds (default: 8 hours)
SAML_SESSION_TTL=28800
```

### Single Logout (SLO)

Enable IdP-initiated and SP-initiated logout:

```bash
SAML_SP_SLO_URL=https://your-app.com/saml/slo
SAML_IDP_SLO_URL=https://idp.company.com/saml/slo
```

---

## API Endpoints

### Initiate Login

```
GET /saml/login?idp=okta&return_to=/dashboard
```

Redirects to IdP for authentication.

### Assertion Consumer Service

```
POST /saml/acs
```

Receives SAML response from IdP.

### Single Logout

```
GET /saml/logout
```

Initiates logout from all sessions.

### Metadata

```
GET /saml/metadata
```

Returns SP metadata XML for IdP configuration.

---

## Multi-Tenant Configuration

### Tenant from SAML Attribute

```bash
# Map tenant from SAML attribute
SAML_ATTR_TENANT_ID=organization
```

The `tenant_id` is used for Row-Level Security:

```yaml
# catalog.yaml
datasets:
  - id: orders
    rls:
      mode: tenant_column
      field: tenant_id
```

### Multiple IdPs

Configure different IdPs per tenant:

```yaml
# config.yaml
saml:
  identity_providers:
    - name: tenant-a-okta
      entity_id: http://www.okta.com/tenant-a
      sso_url: https://tenant-a.okta.com/sso
      x509_cert: "..."
    
    - name: tenant-b-azure
      entity_id: https://sts.windows.net/tenant-b/
      sso_url: https://login.microsoftonline.com/tenant-b/saml2
      x509_cert: "..."
```

---

## Helm Configuration

```yaml
# values.yaml
saml:
  enabled: true
  
  serviceProvider:
    entityId: "https://setupranali.company.com/saml/metadata"
    acsUrl: "https://setupranali.company.com/saml/acs"
    sloUrl: "https://setupranali.company.com/saml/slo"
    
    # From secret
    certSecret: saml-sp-cert
    keySecret: saml-sp-key
  
  identityProviders:
    - name: okta
      entityId: "http://www.okta.com/exk123"
      ssoUrl: "https://company.okta.com/sso/saml"
      # From secret
      certSecret: okta-idp-cert
  
  attributeMapping:
    email: email
    firstName: firstName
    lastName: lastName
    tenantId: organization
    roles: groups
  
  sessionTtl: 28800
  allowApiKeys: true
```

---

## Docker Configuration

```yaml
# docker-compose.yml
services:
  setupranali:
    image: adeygifting/connector
    environment:
      - SAML_ENABLED=true
      - SAML_SP_ENTITY_ID=https://localhost:8080/saml/metadata
      - SAML_SP_ACS_URL=https://localhost:8080/saml/acs
      - SAML_IDP_NAME=okta
      - SAML_IDP_ENTITY_ID=${OKTA_ENTITY_ID}
      - SAML_IDP_SSO_URL=${OKTA_SSO_URL}
      - SAML_IDP_CERT=${OKTA_CERT}
```

---

## Security Best Practices

### 1. Use HTTPS

Always use HTTPS for ACS and SLO URLs:

```bash
SAML_SP_ACS_URL=https://your-app.com/saml/acs
```

### 2. Sign Assertions

Require signed assertions:

```bash
SAML_WANT_ASSERTIONS_SIGNED=true
```

### 3. Encrypt Assertions (Optional)

For sensitive data:

```bash
SAML_WANT_ASSERTIONS_ENCRYPTED=true
SAML_SP_CERT="..."
SAML_SP_PRIVATE_KEY="..."
```

### 4. Validate Certificates

Don't disable strict mode in production:

```bash
SAML_STRICT=true
```

### 5. Short Session TTL

Use reasonable session duration:

```bash
SAML_SESSION_TTL=28800  # 8 hours
```

---

## Troubleshooting

### Signature Validation Failed

```
SAML authentication failed: Signature validation failed
```

**Solutions:**
1. Verify IdP certificate is correct
2. Check certificate hasn't expired
3. Ensure certificate is in PEM format
4. Download fresh certificate from IdP

### Invalid Response

```
SAML authentication failed: Invalid response
```

**Solutions:**
1. Check ACS URL matches IdP configuration
2. Verify Entity ID matches
3. Check clock synchronization
4. Enable debug mode: `SAML_DEBUG=true`

### Assertion Expired

```
SAML authentication failed: Assertion expired
```

**Solutions:**
1. Check server clock is synchronized (NTP)
2. Increase clock skew tolerance in IdP
3. Verify IdP and SP are in same timezone

### Missing Attributes

**Solutions:**
1. Configure attribute statements in IdP
2. Verify attribute mapping names
3. Check user has required attributes in IdP

---

## API Key Fallback

Allow API key authentication when SAML is enabled:

```bash
# Enable both (default)
SAML_ALLOW_API_KEYS=true

# SAML only
SAML_ALLOW_API_KEYS=false
```

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `SAML_ENABLED` | Enable SAML authentication | `false` |
| `SAML_SP_ENTITY_ID` | SP Entity ID | - |
| `SAML_SP_ACS_URL` | Assertion Consumer Service URL | - |
| `SAML_SP_SLO_URL` | Single Logout URL | - |
| `SAML_SP_CERT` | SP X.509 certificate | - |
| `SAML_SP_PRIVATE_KEY` | SP private key | - |
| `SAML_IDP_NAME` | IdP name | `default` |
| `SAML_IDP_ENTITY_ID` | IdP Entity ID | - |
| `SAML_IDP_SSO_URL` | IdP SSO URL | - |
| `SAML_IDP_SLO_URL` | IdP SLO URL | - |
| `SAML_IDP_CERT` | IdP X.509 certificate | - |
| `SAML_ATTR_EMAIL` | Email attribute | `email` |
| `SAML_ATTR_FIRST_NAME` | First name attribute | `firstName` |
| `SAML_ATTR_LAST_NAME` | Last name attribute | `lastName` |
| `SAML_ATTR_TENANT_ID` | Tenant ID attribute | `tenantId` |
| `SAML_ATTR_ROLES` | Roles attribute | `roles` |
| `SAML_SESSION_TTL` | Session TTL (seconds) | `28800` |
| `SAML_STRICT` | Strict validation | `true` |
| `SAML_DEBUG` | Debug mode | `false` |
| `SAML_ALLOW_API_KEYS` | Allow API key fallback | `true` |
| `SAML_WANT_ASSERTIONS_SIGNED` | Require signed assertions | `true` |
| `SAML_WANT_ASSERTIONS_ENCRYPTED` | Require encrypted assertions | `false` |
| `SAML_AUTHN_REQUESTS_SIGNED` | Sign authentication requests | `false` |

