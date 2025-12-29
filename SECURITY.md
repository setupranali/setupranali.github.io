# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please email us at:

📧 **security@setupranali.io**

### What to Include

Please include as much of the following information as possible:

- Type of vulnerability (e.g., SQL injection, authentication bypass, XSS)
- Location of the affected code (file path, line numbers if known)
- Step-by-step instructions to reproduce
- Proof of concept (if available)
- Potential impact
- Suggested fix (if any)

### Response Timeline

| Action | Timeline |
|--------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 1 week |
| Fix development | Depends on severity |
| Security advisory | After fix is released |

### What to Expect

1. **Acknowledgment** — We'll confirm receipt of your report
2. **Assessment** — We'll investigate and determine severity
3. **Communication** — We'll keep you updated on progress
4. **Fix** — We'll develop and test a fix
5. **Release** — We'll release a patched version
6. **Credit** — We'll credit you (unless you prefer anonymity)

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x.x   | ✅ Yes |
| < 1.0   | ❌ No |

---

## Security Best Practices

When deploying SetuPranali, follow these recommendations:

### 1. Encryption Key

```bash
# Generate a strong encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set as environment variable (never commit to git!)
export UBI_SECRET_KEY="your-generated-key"
```

### 2. API Keys

- Use unique API keys per tenant/application
- Rotate keys periodically
- Never log or expose API keys
- Store keys securely (environment variables, secrets manager)

### 3. Network Security

- Always use HTTPS in production
- Place behind a reverse proxy (nginx, Traefik)
- Use firewall rules to restrict access
- Consider VPC/private network deployment

### 4. Database Credentials

- Use service accounts with minimal permissions
- Rotate credentials periodically
- Never commit credentials to git
- Use secrets managers in production

### 5. Rate Limiting

- Enable rate limiting in production
- Configure appropriate limits per tenant
- Monitor for abuse patterns

---

## Security Features

SetuPranali includes these security features:

| Feature | Description |
|---------|-------------|
| **Credential Encryption** | Database credentials encrypted at rest (Fernet/AES) |
| **API Key Authentication** | All protected endpoints require valid API key |
| **Row-Level Security** | Automatic tenant data isolation |
| **No Credential Exposure** | Credentials never returned in API responses |
| **Rate Limiting** | Protection against abuse |
| **Request Logging** | Audit trail (without sensitive data) |

---

## Known Security Considerations

### Development Mode

⚠️ **Warning**: In development mode (no `UBI_SECRET_KEY` set), a fallback key is used. This is **NOT SECURE** for production.

### Credential Storage

Credentials are stored encrypted in SQLite (`sources.db`). For production, consider:

- Encrypting the database file at the OS level
- Using a dedicated secrets manager
- Restricting file permissions

---

## Security Advisories

Security advisories will be published via:

- [GitHub Security Advisories](https://github.com/setupranali/setupranali.github.io/security/advisories)
- Project mailing list (if subscribed)
- Release notes

---

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities.

### Hall of Fame

Contributors who have helped improve our security:

*Be the first to be recognized!*

---

Thank you for helping keep SetuPranali secure! 🛡️

