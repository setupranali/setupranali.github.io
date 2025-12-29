"""
SAML 2.0 SSO Authentication for SetuPranali

Supports enterprise identity providers:
- Okta
- Microsoft ADFS
- Azure AD (SAML)
- OneLogin
- PingFederate
- Shibboleth
- Generic SAML 2.0 IdPs

Features:
- SP-initiated SSO
- IdP-initiated SSO
- Single Logout (SLO)
- Signed assertions
- Encrypted assertions
- Attribute mapping
- Multi-tenant support
"""

import os
import base64
import logging
import hashlib
import secrets
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

# Try to import optional SAML libraries
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.settings import OneLogin_Saml2_Settings
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False
    logger.warning("python3-saml not installed. SAML authentication disabled.")


# =============================================================================
# Configuration Models
# =============================================================================

class SAMLIdentityProvider(BaseModel):
    """SAML Identity Provider configuration."""
    
    name: str = Field(..., description="IdP name (e.g., 'okta', 'adfs')")
    entity_id: str = Field(..., description="IdP Entity ID")
    sso_url: str = Field(..., description="IdP SSO URL (HTTP-Redirect or HTTP-POST)")
    slo_url: Optional[str] = Field(None, description="IdP SLO URL")
    x509_cert: str = Field(..., description="IdP X.509 certificate (PEM format)")
    
    # Optional
    sso_binding: str = Field(default="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect")
    slo_binding: str = Field(default="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect")
    name_id_format: str = Field(default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")


class SAMLServiceProvider(BaseModel):
    """SAML Service Provider (SetuPranali) configuration."""
    
    entity_id: str = Field(..., description="SP Entity ID")
    acs_url: str = Field(..., description="Assertion Consumer Service URL")
    slo_url: Optional[str] = Field(None, description="Single Logout URL")
    metadata_url: Optional[str] = Field(None, description="SP Metadata URL")
    
    # Certificates for signing/encryption
    x509_cert: Optional[str] = Field(None, description="SP X.509 certificate")
    private_key: Optional[str] = Field(None, description="SP private key")
    
    # Options
    want_assertions_signed: bool = Field(default=True)
    want_assertions_encrypted: bool = Field(default=False)
    authn_requests_signed: bool = Field(default=False)
    logout_requests_signed: bool = Field(default=False)


class SAMLAttributeMapping(BaseModel):
    """SAML attribute mapping configuration."""
    
    email: str = Field(default="email", description="Attribute for email")
    first_name: str = Field(default="firstName", description="Attribute for first name")
    last_name: str = Field(default="lastName", description="Attribute for last name")
    display_name: str = Field(default="displayName", description="Attribute for display name")
    tenant_id: str = Field(default="tenantId", description="Attribute for tenant ID")
    roles: str = Field(default="roles", description="Attribute for roles/groups")
    
    # Custom attributes
    custom: Dict[str, str] = Field(default={}, description="Custom attribute mappings")


class SAMLConfig(BaseModel):
    """SAML configuration for SetuPranali."""
    
    enabled: bool = Field(default=False, description="Enable SAML authentication")
    service_provider: SAMLServiceProvider
    identity_providers: List[SAMLIdentityProvider] = Field(default=[])
    default_idp: Optional[str] = Field(None, description="Default IdP name")
    attribute_mapping: SAMLAttributeMapping = Field(default_factory=SAMLAttributeMapping)
    
    # Session
    session_ttl: int = Field(default=28800, description="Session TTL (seconds) - 8 hours")
    
    # Options
    strict: bool = Field(default=True, description="Strict validation")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Fallback
    allow_api_keys: bool = Field(default=True, description="Allow API key authentication")


# =============================================================================
# SAML User Info
# =============================================================================

@dataclass
class SAMLUserInfo:
    """Authenticated SAML user information."""
    
    name_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    session_index: Optional[str] = None
    idp_name: str = ""
    expires_at: Optional[datetime] = None


# =============================================================================
# Session Store
# =============================================================================

class SAMLSessionStore:
    """In-memory session store for SAML sessions."""
    
    def __init__(self, ttl: int = 28800):
        self.ttl = ttl
        self._sessions: Dict[str, Tuple[SAMLUserInfo, float]] = {}
        self._pending_requests: Dict[str, Tuple[str, float]] = {}  # request_id -> (idp_name, timestamp)
    
    def create_session(self, user: SAMLUserInfo) -> str:
        """Create a new session and return session ID."""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=self.ttl)
        user.expires_at = expires_at
        self._sessions[session_id] = (user, expires_at.timestamp())
        self._cleanup()
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SAMLUserInfo]:
        """Get user info from session."""
        if session_id in self._sessions:
            user, expires_at = self._sessions[session_id]
            if datetime.now().timestamp() < expires_at:
                return user
            del self._sessions[session_id]
        return None
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self._sessions.pop(session_id, None)
    
    def store_pending_request(self, request_id: str, idp_name: str) -> None:
        """Store pending SAML request."""
        self._pending_requests[request_id] = (idp_name, datetime.now().timestamp())
    
    def get_pending_request(self, request_id: str) -> Optional[str]:
        """Get IdP name for pending request."""
        if request_id in self._pending_requests:
            idp_name, timestamp = self._pending_requests[request_id]
            # Requests expire after 5 minutes
            if datetime.now().timestamp() - timestamp < 300:
                del self._pending_requests[request_id]
                return idp_name
            del self._pending_requests[request_id]
        return None
    
    def _cleanup(self) -> None:
        """Remove expired sessions."""
        now = datetime.now().timestamp()
        expired = [k for k, (_, exp) in self._sessions.items() if now >= exp]
        for k in expired:
            del self._sessions[k]


# Global session store
_session_store = SAMLSessionStore()


# =============================================================================
# SAML Authenticator
# =============================================================================

class SAMLAuthenticator:
    """SAML 2.0 SSO authenticator for SetuPranali."""
    
    def __init__(self, config: SAMLConfig):
        if not SAML_AVAILABLE:
            raise RuntimeError("python3-saml not installed. Run: pip install python3-saml")
        
        self.config = config
        self.idps: Dict[str, SAMLIdentityProvider] = {}
        
        # Initialize IdPs
        for idp in config.identity_providers:
            self.idps[idp.name] = idp
        
        logger.info(f"SAML initialized with {len(self.idps)} identity providers")
    
    def _get_saml_settings(self, idp: SAMLIdentityProvider, request_data: Dict) -> Dict:
        """Build OneLogin SAML settings dictionary."""
        sp = self.config.service_provider
        
        return {
            "strict": self.config.strict,
            "debug": self.config.debug,
            "sp": {
                "entityId": sp.entity_id,
                "assertionConsumerService": {
                    "url": sp.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": sp.slo_url or "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                } if sp.slo_url else None,
                "NameIDFormat": idp.name_id_format,
                "x509cert": sp.x509_cert or "",
                "privateKey": sp.private_key or "",
            },
            "idp": {
                "entityId": idp.entity_id,
                "singleSignOnService": {
                    "url": idp.sso_url,
                    "binding": idp.sso_binding
                },
                "singleLogoutService": {
                    "url": idp.slo_url or "",
                    "binding": idp.slo_binding
                } if idp.slo_url else None,
                "x509cert": idp.x509_cert,
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": sp.authn_requests_signed,
                "logoutRequestSigned": sp.logout_requests_signed,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": sp.want_assertions_signed,
                "wantAssertionsEncrypted": sp.want_assertions_encrypted,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "wantAttributeStatement": True,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            }
        }
    
    def _prepare_request(self, request: Request) -> Dict:
        """Prepare request data for OneLogin SAML library."""
        url = str(request.url)
        parsed = urlparse(url)
        
        return {
            "https": "on" if parsed.scheme == "https" else "off",
            "http_host": parsed.netloc,
            "script_name": parsed.path,
            "get_data": dict(request.query_params),
            "post_data": {},  # Will be populated for POST requests
        }
    
    def get_idp(self, name: Optional[str] = None) -> SAMLIdentityProvider:
        """Get identity provider by name."""
        if name:
            if name not in self.idps:
                raise HTTPException(status_code=400, detail=f"Unknown IdP: {name}")
            return self.idps[name]
        
        # Use default IdP
        if self.config.default_idp:
            return self.idps.get(self.config.default_idp)
        
        # Use first IdP
        if self.idps:
            return next(iter(self.idps.values()))
        
        raise HTTPException(status_code=500, detail="No identity providers configured")
    
    def initiate_login(
        self,
        request: Request,
        idp_name: Optional[str] = None,
        return_to: Optional[str] = None
    ) -> str:
        """
        Initiate SAML login (SP-initiated SSO).
        
        Returns the redirect URL to the IdP.
        """
        idp = self.get_idp(idp_name)
        request_data = self._prepare_request(request)
        settings = self._get_saml_settings(idp, request_data)
        
        auth = OneLogin_Saml2_Auth(request_data, settings)
        
        # Generate login URL
        redirect_url = auth.login(return_to=return_to)
        
        # Store pending request
        request_id = auth.get_last_request_id()
        if request_id:
            _session_store.store_pending_request(request_id, idp.name)
        
        return redirect_url
    
    async def process_response(
        self,
        request: Request,
        idp_name: Optional[str] = None
    ) -> Tuple[SAMLUserInfo, str]:
        """
        Process SAML response from IdP.
        
        Returns (user_info, session_id).
        """
        # Get form data
        form_data = await request.form()
        
        # Prepare request data
        request_data = self._prepare_request(request)
        request_data["post_data"] = dict(form_data)
        
        # Determine IdP
        if not idp_name:
            # Try to get from RelayState or InResponseTo
            saml_response = form_data.get("SAMLResponse", "")
            if saml_response:
                try:
                    decoded = base64.b64decode(saml_response)
                    # Parse XML to find InResponseTo
                    root = ET.fromstring(decoded)
                    in_response_to = root.get("InResponseTo")
                    if in_response_to:
                        idp_name = _session_store.get_pending_request(in_response_to)
                except Exception:
                    pass
        
        idp = self.get_idp(idp_name)
        settings = self._get_saml_settings(idp, request_data)
        
        auth = OneLogin_Saml2_Auth(request_data, settings)
        auth.process_response()
        
        errors = auth.get_errors()
        if errors:
            error_msg = ", ".join(errors)
            reason = auth.get_last_error_reason()
            logger.error(f"SAML error: {error_msg}. Reason: {reason}")
            raise HTTPException(status_code=401, detail=f"SAML authentication failed: {error_msg}")
        
        if not auth.is_authenticated():
            raise HTTPException(status_code=401, detail="SAML authentication failed")
        
        # Extract user info
        user = self._extract_user_info(auth, idp)
        
        # Create session
        session_id = _session_store.create_session(user)
        
        return user, session_id
    
    def _extract_user_info(
        self,
        auth: "OneLogin_Saml2_Auth",
        idp: SAMLIdentityProvider
    ) -> SAMLUserInfo:
        """Extract user information from SAML response."""
        mapping = self.config.attribute_mapping
        attributes = auth.get_attributes()
        
        def get_attr(name: str) -> Optional[str]:
            """Get single attribute value."""
            values = attributes.get(name, [])
            return values[0] if values else None
        
        def get_attr_list(name: str) -> List[str]:
            """Get attribute as list."""
            return attributes.get(name, [])
        
        return SAMLUserInfo(
            name_id=auth.get_nameid(),
            email=get_attr(mapping.email),
            first_name=get_attr(mapping.first_name),
            last_name=get_attr(mapping.last_name),
            display_name=get_attr(mapping.display_name),
            tenant_id=get_attr(mapping.tenant_id),
            roles=get_attr_list(mapping.roles),
            attributes=attributes,
            session_index=auth.get_session_index(),
            idp_name=idp.name,
        )
    
    def initiate_logout(
        self,
        request: Request,
        session_id: str,
        return_to: Optional[str] = None
    ) -> Optional[str]:
        """
        Initiate SAML logout (SP-initiated SLO).
        
        Returns redirect URL if SLO is configured, None otherwise.
        """
        user = _session_store.get_session(session_id)
        if not user:
            return None
        
        idp = self.get_idp(user.idp_name)
        if not idp.slo_url:
            # No SLO configured, just delete local session
            _session_store.delete_session(session_id)
            return None
        
        request_data = self._prepare_request(request)
        settings = self._get_saml_settings(idp, request_data)
        
        auth = OneLogin_Saml2_Auth(request_data, settings)
        
        redirect_url = auth.logout(
            return_to=return_to,
            name_id=user.name_id,
            session_index=user.session_index
        )
        
        # Delete local session
        _session_store.delete_session(session_id)
        
        return redirect_url
    
    def get_metadata(self) -> str:
        """Generate SP metadata XML."""
        sp = self.config.service_provider
        idp = self.get_idp()
        
        settings = OneLogin_Saml2_Settings({
            "strict": self.config.strict,
            "sp": {
                "entityId": sp.entity_id,
                "assertionConsumerService": {
                    "url": sp.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": sp.slo_url or "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                } if sp.slo_url else None,
                "NameIDFormat": idp.name_id_format,
                "x509cert": sp.x509_cert or "",
            },
            "idp": {
                "entityId": idp.entity_id,
                "singleSignOnService": {
                    "url": idp.sso_url,
                    "binding": idp.sso_binding
                },
                "x509cert": idp.x509_cert,
            }
        })
        
        return settings.get_sp_metadata()
    
    def validate_session(self, session_id: str) -> Optional[SAMLUserInfo]:
        """Validate SAML session and return user info."""
        return _session_store.get_session(session_id)


# =============================================================================
# Global Instance
# =============================================================================

_saml_authenticator: Optional[SAMLAuthenticator] = None


def init_saml(config: SAMLConfig) -> Optional[SAMLAuthenticator]:
    """Initialize SAML authenticator."""
    global _saml_authenticator
    
    if not config.enabled:
        return None
    
    if not SAML_AVAILABLE:
        logger.warning("SAML requested but python3-saml not installed")
        return None
    
    _saml_authenticator = SAMLAuthenticator(config)
    return _saml_authenticator


def get_saml_authenticator() -> Optional[SAMLAuthenticator]:
    """Get SAML authenticator instance."""
    return _saml_authenticator


# =============================================================================
# Configuration Helpers
# =============================================================================

def load_saml_config_from_env() -> SAMLConfig:
    """Load SAML configuration from environment variables."""
    enabled = os.getenv("SAML_ENABLED", "false").lower() == "true"
    
    if not enabled:
        return SAMLConfig(
            enabled=False,
            service_provider=SAMLServiceProvider(
                entity_id="",
                acs_url=""
            )
        )
    
    # Service Provider config
    sp = SAMLServiceProvider(
        entity_id=os.getenv("SAML_SP_ENTITY_ID", ""),
        acs_url=os.getenv("SAML_SP_ACS_URL", ""),
        slo_url=os.getenv("SAML_SP_SLO_URL"),
        metadata_url=os.getenv("SAML_SP_METADATA_URL"),
        x509_cert=os.getenv("SAML_SP_CERT"),
        private_key=os.getenv("SAML_SP_PRIVATE_KEY"),
        want_assertions_signed=os.getenv("SAML_WANT_ASSERTIONS_SIGNED", "true").lower() == "true",
        want_assertions_encrypted=os.getenv("SAML_WANT_ASSERTIONS_ENCRYPTED", "false").lower() == "true",
        authn_requests_signed=os.getenv("SAML_AUTHN_REQUESTS_SIGNED", "false").lower() == "true",
    )
    
    # Identity Providers
    idps = []
    
    # Generic IdP from environment
    if os.getenv("SAML_IDP_ENTITY_ID"):
        idps.append(SAMLIdentityProvider(
            name=os.getenv("SAML_IDP_NAME", "default"),
            entity_id=os.getenv("SAML_IDP_ENTITY_ID", ""),
            sso_url=os.getenv("SAML_IDP_SSO_URL", ""),
            slo_url=os.getenv("SAML_IDP_SLO_URL"),
            x509_cert=os.getenv("SAML_IDP_CERT", ""),
        ))
    
    # Okta
    if os.getenv("SAML_OKTA_METADATA_URL"):
        # Would need to fetch and parse metadata
        pass
    
    # Attribute mapping
    attr_mapping = SAMLAttributeMapping(
        email=os.getenv("SAML_ATTR_EMAIL", "email"),
        first_name=os.getenv("SAML_ATTR_FIRST_NAME", "firstName"),
        last_name=os.getenv("SAML_ATTR_LAST_NAME", "lastName"),
        display_name=os.getenv("SAML_ATTR_DISPLAY_NAME", "displayName"),
        tenant_id=os.getenv("SAML_ATTR_TENANT_ID", "tenantId"),
        roles=os.getenv("SAML_ATTR_ROLES", "roles"),
    )
    
    return SAMLConfig(
        enabled=enabled,
        service_provider=sp,
        identity_providers=idps,
        default_idp=os.getenv("SAML_DEFAULT_IDP"),
        attribute_mapping=attr_mapping,
        session_ttl=int(os.getenv("SAML_SESSION_TTL", "28800")),
        strict=os.getenv("SAML_STRICT", "true").lower() == "true",
        debug=os.getenv("SAML_DEBUG", "false").lower() == "true",
        allow_api_keys=os.getenv("SAML_ALLOW_API_KEYS", "true").lower() == "true",
    )


# =============================================================================
# Pre-configured IdP Helpers
# =============================================================================

def okta_idp(
    domain: str,
    app_id: str,
    x509_cert: str
) -> SAMLIdentityProvider:
    """Create Okta SAML IdP configuration."""
    return SAMLIdentityProvider(
        name="okta",
        entity_id=f"http://www.okta.com/{app_id}",
        sso_url=f"https://{domain}/app/{app_id}/sso/saml",
        slo_url=f"https://{domain}/app/{app_id}/slo/saml",
        x509_cert=x509_cert,
    )


def azure_ad_idp(
    tenant_id: str,
    app_id: str,
    x509_cert: str
) -> SAMLIdentityProvider:
    """Create Azure AD SAML IdP configuration."""
    return SAMLIdentityProvider(
        name="azure",
        entity_id=f"https://sts.windows.net/{tenant_id}/",
        sso_url=f"https://login.microsoftonline.com/{tenant_id}/saml2",
        slo_url=f"https://login.microsoftonline.com/{tenant_id}/saml2",
        x509_cert=x509_cert,
    )


def adfs_idp(
    adfs_url: str,
    x509_cert: str
) -> SAMLIdentityProvider:
    """Create ADFS SAML IdP configuration."""
    return SAMLIdentityProvider(
        name="adfs",
        entity_id=f"{adfs_url}/adfs/services/trust",
        sso_url=f"{adfs_url}/adfs/ls/",
        slo_url=f"{adfs_url}/adfs/ls/",
        x509_cert=x509_cert,
    )


def onelogin_idp(
    subdomain: str,
    connector_id: str,
    x509_cert: str
) -> SAMLIdentityProvider:
    """Create OneLogin SAML IdP configuration."""
    return SAMLIdentityProvider(
        name="onelogin",
        entity_id=f"https://app.onelogin.com/saml/metadata/{connector_id}",
        sso_url=f"https://{subdomain}.onelogin.com/trust/saml2/http-post/sso/{connector_id}",
        slo_url=f"https://{subdomain}.onelogin.com/trust/saml2/http-redirect/slo/{connector_id}",
        x509_cert=x509_cert,
    )


def google_workspace_idp(
    entity_id: str,
    sso_url: str,
    x509_cert: str
) -> SAMLIdentityProvider:
    """Create Google Workspace SAML IdP configuration."""
    return SAMLIdentityProvider(
        name="google",
        entity_id=entity_id,
        sso_url=sso_url,
        x509_cert=x509_cert,
    )

