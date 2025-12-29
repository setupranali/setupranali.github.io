"""
Embedded Analytics for SetuPranali

Provide embed-ready endpoints with secure tokens for embedding
analytics in third-party applications.

Features:
- Embed tokens with scoped permissions
- Iframe-friendly endpoints
- CORS configuration for embedding
- Pre-configured dashboards
- Token-based RLS
"""

import os
import jwt
import uuid
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

EMBED_SECRET_KEY = os.getenv("EMBED_SECRET_KEY", os.getenv("UBI_SECRET_KEY", ""))
EMBED_TOKEN_EXPIRY_HOURS = int(os.getenv("EMBED_TOKEN_EXPIRY_HOURS", "24"))
EMBED_ALLOWED_ORIGINS = os.getenv("EMBED_ALLOWED_ORIGINS", "*").split(",")


class EmbedPermission(str, Enum):
    """Embed permissions."""
    QUERY = "query"
    EXPLORE = "explore"
    EXPORT = "export"
    FILTER = "filter"
    DRILL = "drill"


@dataclass
class EmbedToken:
    """Embedded analytics token."""
    token_id: str
    tenant_id: str
    datasets: List[str]
    permissions: Set[EmbedPermission]
    filters: Dict[str, Any] = field(default_factory=dict)  # Pre-applied filters
    rls_context: Dict[str, Any] = field(default_factory=dict)  # RLS values
    expires_at: datetime = None
    max_rows: int = 10000
    allowed_dimensions: Optional[List[str]] = None  # None = all
    allowed_metrics: Optional[List[str]] = None  # None = all
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbedConfig:
    """Configuration for embedded view."""
    title: Optional[str] = None
    description: Optional[str] = None
    theme: str = "light"  # light, dark, auto
    show_toolbar: bool = True
    show_filters: bool = True
    show_export: bool = False
    allow_fullscreen: bool = True
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None


# =============================================================================
# Token Manager
# =============================================================================

class EmbedTokenManager:
    """Manage embed tokens."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._tokens: Dict[str, EmbedToken] = {}
    
    def create_token(
        self,
        tenant_id: str,
        datasets: List[str],
        permissions: List[str],
        filters: Optional[Dict[str, Any]] = None,
        rls_context: Optional[Dict[str, Any]] = None,
        expiry_hours: int = EMBED_TOKEN_EXPIRY_HOURS,
        max_rows: int = 10000,
        allowed_dimensions: Optional[List[str]] = None,
        allowed_metrics: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an embed token."""
        token_id = str(uuid.uuid4())
        
        # Parse permissions
        perms = set()
        for p in permissions:
            try:
                perms.add(EmbedPermission(p))
            except ValueError:
                logger.warning(f"Unknown permission: {p}")
        
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        embed_token = EmbedToken(
            token_id=token_id,
            tenant_id=tenant_id,
            datasets=datasets,
            permissions=perms,
            filters=filters or {},
            rls_context=rls_context or {},
            expires_at=expires_at,
            max_rows=max_rows,
            allowed_dimensions=allowed_dimensions,
            allowed_metrics=allowed_metrics,
            metadata=metadata or {}
        )
        
        # Store token
        self._tokens[token_id] = embed_token
        
        # Create JWT
        payload = {
            "token_id": token_id,
            "tenant_id": tenant_id,
            "datasets": datasets,
            "permissions": [p.value for p in perms],
            "exp": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "type": "embed"
        }
        
        jwt_token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return jwt_token
    
    def validate_token(self, jwt_token: str) -> Optional[EmbedToken]:
        """Validate an embed token."""
        try:
            payload = jwt.decode(jwt_token, self.secret_key, algorithms=["HS256"])
            
            # Check token type
            if payload.get("type") != "embed":
                return None
            
            token_id = payload.get("token_id")
            
            # Get stored token
            embed_token = self._tokens.get(token_id)
            if not embed_token:
                # Token not in memory, recreate from JWT
                embed_token = EmbedToken(
                    token_id=token_id,
                    tenant_id=payload.get("tenant_id", ""),
                    datasets=payload.get("datasets", []),
                    permissions={EmbedPermission(p) for p in payload.get("permissions", [])},
                    expires_at=datetime.fromtimestamp(payload.get("exp", 0))
                )
            
            # Check expiry
            if datetime.utcnow() > embed_token.expires_at:
                return None
            
            return embed_token
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke an embed token."""
        if token_id in self._tokens:
            del self._tokens[token_id]
            return True
        return False
    
    def list_tokens(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active tokens."""
        tokens = []
        now = datetime.utcnow()
        
        for token in self._tokens.values():
            if token.expires_at < now:
                continue
            
            if tenant_id and token.tenant_id != tenant_id:
                continue
            
            tokens.append({
                "token_id": token.token_id,
                "tenant_id": token.tenant_id,
                "datasets": token.datasets,
                "permissions": [p.value for p in token.permissions],
                "expires_at": token.expires_at.isoformat(),
                "max_rows": token.max_rows
            })
        
        return tokens


# =============================================================================
# Embed HTML Generator
# =============================================================================

class EmbedHtmlGenerator:
    """Generate embeddable HTML/iframe content."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    def generate_iframe_url(
        self,
        token: str,
        config: Optional[EmbedConfig] = None
    ) -> str:
        """Generate iframe URL for embedding."""
        config = config or EmbedConfig()
        
        params = [
            f"token={token}",
            f"theme={config.theme}",
            f"toolbar={str(config.show_toolbar).lower()}",
            f"filters={str(config.show_filters).lower()}",
            f"export={str(config.show_export).lower()}"
        ]
        
        return f"{self.base_url}/embed/view?{'&'.join(params)}"
    
    def generate_iframe_html(
        self,
        token: str,
        config: Optional[EmbedConfig] = None,
        width: str = "100%",
        height: str = "600px"
    ) -> str:
        """Generate complete iframe HTML snippet."""
        url = self.generate_iframe_url(token, config)
        config = config or EmbedConfig()
        
        allow_attrs = ["accelerometer", "clipboard-write", "encrypted-media"]
        if config.allow_fullscreen:
            allow_attrs.append("fullscreen")
        
        return f'''<iframe
  src="{url}"
  width="{width}"
  height="{height}"
  frameborder="0"
  allow="{'; '.join(allow_attrs)}"
  {' allowfullscreen' if config.allow_fullscreen else ''}
  style="border: none; border-radius: 8px;"
></iframe>'''
    
    def generate_js_snippet(
        self,
        token: str,
        container_id: str,
        config: Optional[EmbedConfig] = None
    ) -> str:
        """Generate JavaScript snippet for embedding."""
        config = config or EmbedConfig()
        
        return f'''<script src="{self.base_url}/embed/sdk.js"></script>
<script>
  SetuPranali.embed({{
    container: '#{container_id}',
    token: '{token}',
    theme: '{config.theme}',
    showToolbar: {str(config.show_toolbar).lower()},
    showFilters: {str(config.show_filters).lower()},
    showExport: {str(config.show_export).lower()},
    allowFullscreen: {str(config.allow_fullscreen).lower()}
  }});
</script>'''


# =============================================================================
# Embedded Query Handler
# =============================================================================

class EmbeddedQueryHandler:
    """Handle queries from embedded views."""
    
    def __init__(self, token_manager: EmbedTokenManager):
        self.token_manager = token_manager
    
    def validate_and_process_query(
        self,
        jwt_token: str,
        query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate token and process embedded query."""
        # Validate token
        embed_token = self.token_manager.validate_token(jwt_token)
        if not embed_token:
            return {
                "error": "Invalid or expired embed token",
                "code": "EMBED_TOKEN_INVALID"
            }
        
        # Check dataset access
        dataset = query.get("dataset")
        if dataset not in embed_token.datasets:
            return {
                "error": f"Dataset '{dataset}' not allowed for this embed token",
                "code": "EMBED_DATASET_DENIED"
            }
        
        # Check permission
        if EmbedPermission.QUERY not in embed_token.permissions:
            return {
                "error": "Query permission not granted",
                "code": "EMBED_PERMISSION_DENIED"
            }
        
        # Apply dimension/metric restrictions
        if embed_token.allowed_dimensions is not None:
            query_dims = set(query.get("dimensions", []))
            allowed = set(embed_token.allowed_dimensions)
            if not query_dims.issubset(allowed):
                denied = query_dims - allowed
                return {
                    "error": f"Dimensions not allowed: {denied}",
                    "code": "EMBED_DIMENSION_DENIED"
                }
        
        if embed_token.allowed_metrics is not None:
            query_metrics = set(query.get("metrics", []))
            allowed = set(embed_token.allowed_metrics)
            if not query_metrics.issubset(allowed):
                denied = query_metrics - allowed
                return {
                    "error": f"Metrics not allowed: {denied}",
                    "code": "EMBED_METRIC_DENIED"
                }
        
        # Apply pre-configured filters
        if embed_token.filters:
            query_filters = query.get("filters", {})
            query["filters"] = {**embed_token.filters, **query_filters}
        
        # Apply row limit
        if query.get("limit", float("inf")) > embed_token.max_rows:
            query["limit"] = embed_token.max_rows
        
        return {
            "query": query,
            "tenant_id": embed_token.tenant_id,
            "rls_context": embed_token.rls_context,
            "validated": True
        }


# =============================================================================
# Embed Service
# =============================================================================

class EmbedAnalyticsService:
    """Service for embedded analytics."""
    
    def __init__(self, secret_key: str, base_url: str):
        self.token_manager = EmbedTokenManager(secret_key)
        self.html_generator = EmbedHtmlGenerator(base_url)
        self.query_handler = EmbeddedQueryHandler(self.token_manager)
    
    def create_embed_token(
        self,
        tenant_id: str,
        datasets: List[str],
        permissions: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create an embed token."""
        permissions = permissions or ["query", "filter"]
        
        token = self.token_manager.create_token(
            tenant_id=tenant_id,
            datasets=datasets,
            permissions=permissions,
            **kwargs
        )
        
        return {
            "token": token,
            "type": "embed",
            "expires_in_hours": kwargs.get("expiry_hours", EMBED_TOKEN_EXPIRY_HOURS)
        }
    
    def get_embed_code(
        self,
        token: str,
        format: str = "iframe",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get embeddable code snippet."""
        embed_config = EmbedConfig(**(config or {}))
        
        if format == "iframe":
            return {
                "html": self.html_generator.generate_iframe_html(token, embed_config),
                "url": self.html_generator.generate_iframe_url(token, embed_config)
            }
        elif format == "js":
            return {
                "html": self.html_generator.generate_js_snippet(token, "setupranali-embed", embed_config),
                "container_id": "setupranali-embed"
            }
        else:
            return {"url": self.html_generator.generate_iframe_url(token, embed_config)}
    
    def validate_query(
        self,
        token: str,
        query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and prepare query for execution."""
        return self.query_handler.validate_and_process_query(token, query)
    
    def list_tokens(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active embed tokens."""
        return self.token_manager.list_tokens(tenant_id)
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke an embed token."""
        return self.token_manager.revoke_token(token_id)


# =============================================================================
# Global Service
# =============================================================================

_embed_service: Optional[EmbedAnalyticsService] = None


def get_embed_service() -> EmbedAnalyticsService:
    """Get embed analytics service singleton."""
    global _embed_service
    if not _embed_service:
        base_url = os.getenv("BASE_URL", "http://localhost:8080")
        _embed_service = EmbedAnalyticsService(EMBED_SECRET_KEY, base_url)
    return _embed_service

