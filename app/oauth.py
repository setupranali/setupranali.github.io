"""
OAuth 2.0 / OIDC Authentication for SetuPranali

Supports multiple OAuth providers:
- Google
- Microsoft Azure AD
- Okta
- Auth0
- Keycloak
- Generic OIDC providers

Features:
- JWT token validation
- JWKS (JSON Web Key Set) caching
- Token introspection
- Automatic key rotation
- Role/scope mapping
- Multi-tenant support
"""

import os
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.parse import urljoin

import jwt
import requests
from pydantic import BaseModel, Field
from fastapi import HTTPException, Request, Depends
from fastapi.security import OAuth2AuthorizationCodeBearer, HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Models
# =============================================================================

class OAuthProvider(BaseModel):
    """OAuth provider configuration."""
    
    name: str = Field(..., description="Provider name (e.g., 'google', 'azure', 'okta')")
    issuer: str = Field(..., description="OAuth issuer URL")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
    
    # Discovery
    discovery_url: Optional[str] = Field(None, description="OIDC discovery URL (.well-known/openid-configuration)")
    jwks_uri: Optional[str] = Field(None, description="JWKS endpoint URL")
    
    # Endpoints (auto-discovered if discovery_url provided)
    authorization_url: Optional[str] = Field(None, description="Authorization endpoint")
    token_url: Optional[str] = Field(None, description="Token endpoint")
    userinfo_url: Optional[str] = Field(None, description="Userinfo endpoint")
    introspection_url: Optional[str] = Field(None, description="Token introspection endpoint")
    
    # Validation
    audience: Optional[str] = Field(None, description="Expected audience (aud claim)")
    scopes: List[str] = Field(default=["openid", "profile", "email"], description="Required scopes")
    
    # Mapping
    tenant_claim: str = Field(default="tenant_id", description="Claim containing tenant ID")
    roles_claim: str = Field(default="roles", description="Claim containing user roles")
    email_claim: str = Field(default="email", description="Claim containing user email")
    
    # Options
    verify_exp: bool = Field(default=True, description="Verify token expiration")
    verify_aud: bool = Field(default=True, description="Verify audience")
    leeway: int = Field(default=60, description="Leeway for time-based claims (seconds)")
    cache_ttl: int = Field(default=3600, description="JWKS cache TTL (seconds)")


class OAuthConfig(BaseModel):
    """OAuth configuration for SetuPranali."""
    
    enabled: bool = Field(default=False, description="Enable OAuth authentication")
    providers: List[OAuthProvider] = Field(default=[], description="OAuth providers")
    default_provider: Optional[str] = Field(None, description="Default provider name")
    
    # Fallback to API keys
    allow_api_keys: bool = Field(default=True, description="Allow API key authentication as fallback")
    
    # Session
    session_ttl: int = Field(default=3600, description="Session TTL (seconds)")


# =============================================================================
# JWKS Cache
# =============================================================================

class JWKSCache:
    """Cache for JSON Web Key Sets."""
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Dict, float]] = {}
    
    def get(self, uri: str) -> Optional[Dict]:
        """Get JWKS from cache."""
        if uri in self._cache:
            jwks, expires_at = self._cache[uri]
            if time.time() < expires_at:
                return jwks
            del self._cache[uri]
        return None
    
    def set(self, uri: str, jwks: Dict) -> None:
        """Set JWKS in cache."""
        expires_at = time.time() + self.ttl
        self._cache[uri] = (jwks, expires_at)
    
    def fetch(self, uri: str) -> Dict:
        """Fetch JWKS from URI with caching."""
        cached = self.get(uri)
        if cached:
            return cached
        
        try:
            response = requests.get(uri, timeout=10)
            response.raise_for_status()
            jwks = response.json()
            self.set(uri, jwks)
            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {uri}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch signing keys")


# Global JWKS cache
_jwks_cache = JWKSCache()


# =============================================================================
# OAuth Provider Discovery
# =============================================================================

def discover_provider(provider: OAuthProvider) -> OAuthProvider:
    """Discover OAuth provider configuration from OIDC discovery endpoint."""
    if not provider.discovery_url:
        # Try to construct discovery URL from issuer
        provider.discovery_url = urljoin(
            provider.issuer.rstrip("/") + "/",
            ".well-known/openid-configuration"
        )
    
    try:
        response = requests.get(provider.discovery_url, timeout=10)
        response.raise_for_status()
        config = response.json()
        
        # Update provider with discovered values
        if not provider.jwks_uri:
            provider.jwks_uri = config.get("jwks_uri")
        if not provider.authorization_url:
            provider.authorization_url = config.get("authorization_endpoint")
        if not provider.token_url:
            provider.token_url = config.get("token_endpoint")
        if not provider.userinfo_url:
            provider.userinfo_url = config.get("userinfo_endpoint")
        if not provider.introspection_url:
            provider.introspection_url = config.get("introspection_endpoint")
        
        logger.info(f"Discovered OAuth provider: {provider.name}")
        return provider
        
    except Exception as e:
        logger.warning(f"Failed to discover provider {provider.name}: {e}")
        return provider


# =============================================================================
# Token Validation
# =============================================================================

class TokenInfo(BaseModel):
    """Validated token information."""
    
    sub: str = Field(..., description="Subject (user ID)")
    email: Optional[str] = Field(None, description="User email")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    roles: List[str] = Field(default=[], description="User roles")
    scopes: List[str] = Field(default=[], description="Token scopes")
    provider: str = Field(..., description="OAuth provider name")
    expires_at: Optional[datetime] = Field(None, description="Token expiration")
    raw_claims: Dict[str, Any] = Field(default={}, description="Raw JWT claims")


def get_signing_key(token: str, provider: OAuthProvider) -> Any:
    """Get signing key for token validation."""
    if not provider.jwks_uri:
        raise HTTPException(status_code=500, detail="JWKS URI not configured")
    
    # Get JWKS
    jwks = _jwks_cache.fetch(provider.jwks_uri)
    
    # Decode token header to get kid
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing key ID (kid)")
    
    # Find matching key
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    
    raise HTTPException(status_code=401, detail="Signing key not found")


def validate_token(token: str, provider: OAuthProvider) -> TokenInfo:
    """Validate JWT token and extract claims."""
    try:
        # Get signing key
        signing_key = get_signing_key(token, provider)
        
        # Build validation options
        options = {
            "verify_signature": True,
            "verify_exp": provider.verify_exp,
            "verify_aud": provider.verify_aud,
            "require": ["sub"],
        }
        
        # Decode and validate token
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "RS384", "RS512"],
            audience=provider.audience if provider.verify_aud else None,
            issuer=provider.issuer,
            leeway=provider.leeway,
            options=options,
        )
        
        # Extract claims
        token_info = TokenInfo(
            sub=claims.get("sub"),
            email=claims.get(provider.email_claim),
            tenant_id=claims.get(provider.tenant_claim),
            roles=claims.get(provider.roles_claim, []),
            scopes=claims.get("scope", "").split() if isinstance(claims.get("scope"), str) else claims.get("scope", []),
            provider=provider.name,
            expires_at=datetime.fromtimestamp(claims["exp"]) if "exp" in claims else None,
            raw_claims=claims,
        )
        
        return token_info
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token issuer")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


# =============================================================================
# OAuth Authenticator
# =============================================================================

class OAuthAuthenticator:
    """OAuth 2.0 / OIDC authenticator for SetuPranali."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.providers: Dict[str, OAuthProvider] = {}
        
        # Initialize providers
        for provider in config.providers:
            discovered = discover_provider(provider)
            self.providers[provider.name] = discovered
        
        logger.info(f"OAuth initialized with {len(self.providers)} providers")
    
    def get_provider(self, name: Optional[str] = None) -> OAuthProvider:
        """Get OAuth provider by name."""
        if name:
            if name not in self.providers:
                raise HTTPException(status_code=400, detail=f"Unknown OAuth provider: {name}")
            return self.providers[name]
        
        # Use default provider
        if self.config.default_provider:
            return self.providers.get(self.config.default_provider)
        
        # Use first provider
        if self.providers:
            return next(iter(self.providers.values()))
        
        raise HTTPException(status_code=500, detail="No OAuth providers configured")
    
    def authenticate(self, token: str, provider_name: Optional[str] = None) -> TokenInfo:
        """Authenticate using OAuth token."""
        if not self.config.enabled:
            raise HTTPException(status_code=500, detail="OAuth authentication not enabled")
        
        provider = self.get_provider(provider_name)
        return validate_token(token, provider)
    
    def authenticate_from_header(
        self,
        authorization: str,
        provider_name: Optional[str] = None
    ) -> TokenInfo:
        """Authenticate from Authorization header."""
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Parse Bearer token
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = parts[1]
        return self.authenticate(token, provider_name)


# =============================================================================
# FastAPI Dependencies
# =============================================================================

# Global authenticator instance
_oauth_authenticator: Optional[OAuthAuthenticator] = None


def init_oauth(config: OAuthConfig) -> OAuthAuthenticator:
    """Initialize OAuth authenticator."""
    global _oauth_authenticator
    _oauth_authenticator = OAuthAuthenticator(config)
    return _oauth_authenticator


def get_oauth_authenticator() -> OAuthAuthenticator:
    """Get OAuth authenticator instance."""
    if not _oauth_authenticator:
        raise HTTPException(status_code=500, detail="OAuth not initialized")
    return _oauth_authenticator


# Security scheme
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_oauth_token_info(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
) -> Optional[TokenInfo]:
    """
    FastAPI dependency to get OAuth token info.
    
    Returns None if OAuth is disabled or no token provided,
    allowing fallback to API key authentication.
    """
    global _oauth_authenticator
    
    if not _oauth_authenticator or not _oauth_authenticator.config.enabled:
        return None
    
    if not credentials:
        return None
    
    # Get provider from header if specified
    provider_name = request.headers.get("X-OAuth-Provider")
    
    try:
        return _oauth_authenticator.authenticate(credentials.credentials, provider_name)
    except HTTPException:
        if _oauth_authenticator.config.allow_api_keys:
            return None  # Allow fallback to API key
        raise


# =============================================================================
# Configuration Helpers
# =============================================================================

def load_oauth_config_from_env() -> OAuthConfig:
    """Load OAuth configuration from environment variables."""
    enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
    
    if not enabled:
        return OAuthConfig(enabled=False)
    
    providers = []
    
    # Google
    if os.getenv("OAUTH_GOOGLE_CLIENT_ID"):
        providers.append(OAuthProvider(
            name="google",
            issuer="https://accounts.google.com",
            client_id=os.getenv("OAUTH_GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_GOOGLE_CLIENT_SECRET"),
            audience=os.getenv("OAUTH_GOOGLE_CLIENT_ID", ""),
        ))
    
    # Microsoft Azure AD
    if os.getenv("OAUTH_AZURE_CLIENT_ID"):
        tenant_id = os.getenv("OAUTH_AZURE_TENANT_ID", "common")
        providers.append(OAuthProvider(
            name="azure",
            issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            client_id=os.getenv("OAUTH_AZURE_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_AZURE_CLIENT_SECRET"),
            audience=os.getenv("OAUTH_AZURE_CLIENT_ID", ""),
        ))
    
    # Okta
    if os.getenv("OAUTH_OKTA_DOMAIN"):
        providers.append(OAuthProvider(
            name="okta",
            issuer=f"https://{os.getenv('OAUTH_OKTA_DOMAIN')}",
            client_id=os.getenv("OAUTH_OKTA_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_OKTA_CLIENT_SECRET"),
            audience=os.getenv("OAUTH_OKTA_AUDIENCE", "api://default"),
        ))
    
    # Auth0
    if os.getenv("OAUTH_AUTH0_DOMAIN"):
        providers.append(OAuthProvider(
            name="auth0",
            issuer=f"https://{os.getenv('OAUTH_AUTH0_DOMAIN')}/",
            client_id=os.getenv("OAUTH_AUTH0_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_AUTH0_CLIENT_SECRET"),
            audience=os.getenv("OAUTH_AUTH0_AUDIENCE", ""),
        ))
    
    # Keycloak
    if os.getenv("OAUTH_KEYCLOAK_URL"):
        realm = os.getenv("OAUTH_KEYCLOAK_REALM", "master")
        providers.append(OAuthProvider(
            name="keycloak",
            issuer=f"{os.getenv('OAUTH_KEYCLOAK_URL')}/realms/{realm}",
            client_id=os.getenv("OAUTH_KEYCLOAK_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_KEYCLOAK_CLIENT_SECRET"),
        ))
    
    # Generic OIDC
    if os.getenv("OAUTH_OIDC_ISSUER"):
        providers.append(OAuthProvider(
            name="oidc",
            issuer=os.getenv("OAUTH_OIDC_ISSUER", ""),
            client_id=os.getenv("OAUTH_OIDC_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_OIDC_CLIENT_SECRET"),
            audience=os.getenv("OAUTH_OIDC_AUDIENCE"),
            discovery_url=os.getenv("OAUTH_OIDC_DISCOVERY_URL"),
        ))
    
    return OAuthConfig(
        enabled=enabled,
        providers=providers,
        default_provider=os.getenv("OAUTH_DEFAULT_PROVIDER"),
        allow_api_keys=os.getenv("OAUTH_ALLOW_API_KEYS", "true").lower() == "true",
    )


# =============================================================================
# Pre-configured Providers
# =============================================================================

def google_provider(client_id: str, client_secret: Optional[str] = None) -> OAuthProvider:
    """Create Google OAuth provider."""
    return OAuthProvider(
        name="google",
        issuer="https://accounts.google.com",
        client_id=client_id,
        client_secret=client_secret,
        audience=client_id,
        email_claim="email",
    )


def azure_provider(
    client_id: str,
    tenant_id: str = "common",
    client_secret: Optional[str] = None
) -> OAuthProvider:
    """Create Microsoft Azure AD OAuth provider."""
    return OAuthProvider(
        name="azure",
        issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        client_id=client_id,
        client_secret=client_secret,
        audience=client_id,
        roles_claim="roles",
        tenant_claim="tid",
    )


def okta_provider(
    domain: str,
    client_id: str,
    client_secret: Optional[str] = None,
    audience: str = "api://default"
) -> OAuthProvider:
    """Create Okta OAuth provider."""
    return OAuthProvider(
        name="okta",
        issuer=f"https://{domain}",
        client_id=client_id,
        client_secret=client_secret,
        audience=audience,
    )


def auth0_provider(
    domain: str,
    client_id: str,
    audience: str,
    client_secret: Optional[str] = None
) -> OAuthProvider:
    """Create Auth0 OAuth provider."""
    return OAuthProvider(
        name="auth0",
        issuer=f"https://{domain}/",
        client_id=client_id,
        client_secret=client_secret,
        audience=audience,
    )


def keycloak_provider(
    url: str,
    realm: str,
    client_id: str,
    client_secret: Optional[str] = None
) -> OAuthProvider:
    """Create Keycloak OAuth provider."""
    return OAuthProvider(
        name="keycloak",
        issuer=f"{url}/realms/{realm}",
        client_id=client_id,
        client_secret=client_secret,
        roles_claim="realm_access.roles",
    )

