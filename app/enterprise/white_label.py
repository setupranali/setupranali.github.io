"""
White-Label Support for SetuPranali

Custom branding for OEM deployments and multi-tenant environments.

Features:
- Custom branding per tenant
- Logo and color customization
- Custom domain mapping
- Email template customization
- Footer/header customization
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Models
# =============================================================================

@dataclass
class BrandingColors:
    """Brand color palette."""
    primary: str = "#6366F1"  # Indigo
    secondary: str = "#8B5CF6"  # Purple
    accent: str = "#06B6D4"  # Cyan
    background: str = "#FFFFFF"
    surface: str = "#F9FAFB"
    text: str = "#111827"
    text_secondary: str = "#6B7280"
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"


@dataclass
class BrandingAssets:
    """Brand assets."""
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    background_image_url: Optional[str] = None
    custom_css_url: Optional[str] = None
    custom_js_url: Optional[str] = None


@dataclass
class BrandingText:
    """Brand text customization."""
    company_name: str = "SetuPranali"
    product_name: str = "Analytics"
    tagline: Optional[str] = None
    footer_text: Optional[str] = None
    copyright_text: Optional[str] = None
    support_email: Optional[str] = None
    docs_url: Optional[str] = None


@dataclass
class WhiteLabelConfig:
    """Complete white-label configuration."""
    tenant_id: str
    enabled: bool = True
    colors: BrandingColors = field(default_factory=BrandingColors)
    assets: BrandingAssets = field(default_factory=BrandingAssets)
    text: BrandingText = field(default_factory=BrandingText)
    custom_domain: Optional[str] = None
    features: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# White-Label Manager
# =============================================================================

class WhiteLabelManager:
    """Manage white-label configurations."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else None
        self._configs: Dict[str, WhiteLabelConfig] = {}
        self._domain_mapping: Dict[str, str] = {}  # domain -> tenant_id
        self._default_config: Optional[WhiteLabelConfig] = None
        
        if self.config_path and self.config_path.exists():
            self._load_configs()
    
    def _load_configs(self) -> None:
        """Load configurations from file."""
        try:
            with open(self.config_path) as f:
                data = yaml.safe_load(f)
            
            # Load default config
            if "default" in data:
                self._default_config = self._parse_config("default", data["default"])
            
            # Load tenant configs
            for tenant_id, config_data in data.get("tenants", {}).items():
                config = self._parse_config(tenant_id, config_data)
                self._configs[tenant_id] = config
                
                # Map custom domain
                if config.custom_domain:
                    self._domain_mapping[config.custom_domain] = tenant_id
            
            logger.info(f"Loaded {len(self._configs)} white-label configurations")
            
        except Exception as e:
            logger.error(f"Failed to load white-label configs: {e}")
    
    def _parse_config(self, tenant_id: str, data: Dict[str, Any]) -> WhiteLabelConfig:
        """Parse configuration from dict."""
        colors = BrandingColors(**data.get("colors", {}))
        assets = BrandingAssets(**data.get("assets", {}))
        text = BrandingText(**data.get("text", {}))
        
        return WhiteLabelConfig(
            tenant_id=tenant_id,
            enabled=data.get("enabled", True),
            colors=colors,
            assets=assets,
            text=text,
            custom_domain=data.get("custom_domain"),
            features=data.get("features", {}),
            metadata=data.get("metadata", {})
        )
    
    def get_config(self, tenant_id: str) -> WhiteLabelConfig:
        """Get white-label config for tenant."""
        if tenant_id in self._configs:
            return self._configs[tenant_id]
        
        if self._default_config:
            # Return default with tenant_id
            config = WhiteLabelConfig(
                tenant_id=tenant_id,
                colors=self._default_config.colors,
                assets=self._default_config.assets,
                text=self._default_config.text
            )
            return config
        
        return WhiteLabelConfig(tenant_id=tenant_id)
    
    def get_config_by_domain(self, domain: str) -> Optional[WhiteLabelConfig]:
        """Get white-label config by custom domain."""
        tenant_id = self._domain_mapping.get(domain)
        if tenant_id:
            return self._configs.get(tenant_id)
        return None
    
    def set_config(self, config: WhiteLabelConfig) -> None:
        """Set or update white-label config."""
        self._configs[config.tenant_id] = config
        
        if config.custom_domain:
            self._domain_mapping[config.custom_domain] = config.tenant_id
    
    def delete_config(self, tenant_id: str) -> bool:
        """Delete white-label config."""
        if tenant_id in self._configs:
            config = self._configs[tenant_id]
            
            # Remove domain mapping
            if config.custom_domain:
                self._domain_mapping.pop(config.custom_domain, None)
            
            del self._configs[tenant_id]
            return True
        return False
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """List all white-label configs."""
        return [
            {
                "tenant_id": config.tenant_id,
                "company_name": config.text.company_name,
                "custom_domain": config.custom_domain,
                "enabled": config.enabled
            }
            for config in self._configs.values()
        ]
    
    def save_configs(self) -> None:
        """Save configurations to file."""
        if not self.config_path:
            return
        
        data = {"tenants": {}}
        
        if self._default_config:
            data["default"] = self._config_to_dict(self._default_config)
        
        for tenant_id, config in self._configs.items():
            data["tenants"][tenant_id] = self._config_to_dict(config)
        
        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def _config_to_dict(self, config: WhiteLabelConfig) -> Dict[str, Any]:
        """Convert config to dict for serialization."""
        return {
            "enabled": config.enabled,
            "colors": {
                "primary": config.colors.primary,
                "secondary": config.colors.secondary,
                "accent": config.colors.accent,
                "background": config.colors.background,
                "surface": config.colors.surface,
                "text": config.colors.text,
                "text_secondary": config.colors.text_secondary,
                "success": config.colors.success,
                "warning": config.colors.warning,
                "error": config.colors.error,
            },
            "assets": {
                "logo_url": config.assets.logo_url,
                "logo_dark_url": config.assets.logo_dark_url,
                "favicon_url": config.assets.favicon_url,
                "background_image_url": config.assets.background_image_url,
                "custom_css_url": config.assets.custom_css_url,
                "custom_js_url": config.assets.custom_js_url,
            },
            "text": {
                "company_name": config.text.company_name,
                "product_name": config.text.product_name,
                "tagline": config.text.tagline,
                "footer_text": config.text.footer_text,
                "copyright_text": config.text.copyright_text,
                "support_email": config.text.support_email,
                "docs_url": config.text.docs_url,
            },
            "custom_domain": config.custom_domain,
            "features": config.features,
            "metadata": config.metadata,
        }


# =============================================================================
# CSS Generator
# =============================================================================

class BrandingCssGenerator:
    """Generate CSS for white-label branding."""
    
    def generate_css_variables(self, config: WhiteLabelConfig) -> str:
        """Generate CSS custom properties for branding."""
        colors = config.colors
        
        return f""":root {{
  --brand-primary: {colors.primary};
  --brand-secondary: {colors.secondary};
  --brand-accent: {colors.accent};
  --brand-background: {colors.background};
  --brand-surface: {colors.surface};
  --brand-text: {colors.text};
  --brand-text-secondary: {colors.text_secondary};
  --brand-success: {colors.success};
  --brand-warning: {colors.warning};
  --brand-error: {colors.error};
  
  /* Computed colors */
  --brand-primary-light: {self._lighten(colors.primary, 0.2)};
  --brand-primary-dark: {self._darken(colors.primary, 0.2)};
}}

/* Dark mode */
.dark {{
  --brand-background: #111827;
  --brand-surface: #1F2937;
  --brand-text: #F9FAFB;
  --brand-text-secondary: #9CA3AF;
}}
"""
    
    def generate_full_css(self, config: WhiteLabelConfig) -> str:
        """Generate complete CSS for branding."""
        css = self.generate_css_variables(config)
        
        # Add component styles
        css += f"""
/* Branding overrides */
.brand-header {{
  background-color: var(--brand-primary);
  color: white;
}}

.brand-logo {{
  {f'background-image: url({config.assets.logo_url});' if config.assets.logo_url else ''}
}}

.brand-button-primary {{
  background-color: var(--brand-primary);
  color: white;
}}

.brand-button-primary:hover {{
  background-color: var(--brand-primary-dark);
}}

.brand-link {{
  color: var(--brand-primary);
}}

.brand-footer {{
  background-color: var(--brand-surface);
  color: var(--brand-text-secondary);
}}
"""
        return css
    
    def _lighten(self, hex_color: str, amount: float) -> str:
        """Lighten a hex color."""
        return self._adjust_color(hex_color, amount)
    
    def _darken(self, hex_color: str, amount: float) -> str:
        """Darken a hex color."""
        return self._adjust_color(hex_color, -amount)
    
    def _adjust_color(self, hex_color: str, amount: float) -> str:
        """Adjust hex color brightness."""
        hex_color = hex_color.lstrip("#")
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, max(0, int(r + (255 if amount > 0 else 0 - r) * abs(amount))))
        g = min(255, max(0, int(g + (255 if amount > 0 else 0 - g) * abs(amount))))
        b = min(255, max(0, int(b + (255 if amount > 0 else 0 - b) * abs(amount))))
        
        return f"#{r:02x}{g:02x}{b:02x}"


# =============================================================================
# White-Label Service
# =============================================================================

class WhiteLabelService:
    """Service for white-label functionality."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.manager = WhiteLabelManager(config_path)
        self.css_generator = BrandingCssGenerator()
    
    def get_branding(self, tenant_id: str) -> Dict[str, Any]:
        """Get branding configuration for tenant."""
        config = self.manager.get_config(tenant_id)
        
        return {
            "tenant_id": config.tenant_id,
            "enabled": config.enabled,
            "colors": {
                "primary": config.colors.primary,
                "secondary": config.colors.secondary,
                "accent": config.colors.accent,
                "background": config.colors.background,
                "surface": config.colors.surface,
                "text": config.colors.text,
                "textSecondary": config.colors.text_secondary,
                "success": config.colors.success,
                "warning": config.colors.warning,
                "error": config.colors.error,
            },
            "assets": {
                "logoUrl": config.assets.logo_url,
                "logoDarkUrl": config.assets.logo_dark_url,
                "faviconUrl": config.assets.favicon_url,
                "backgroundImageUrl": config.assets.background_image_url,
            },
            "text": {
                "companyName": config.text.company_name,
                "productName": config.text.product_name,
                "tagline": config.text.tagline,
                "footerText": config.text.footer_text,
                "copyrightText": config.text.copyright_text,
                "supportEmail": config.text.support_email,
                "docsUrl": config.text.docs_url,
            },
            "customDomain": config.custom_domain,
            "features": config.features
        }
    
    def get_branding_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get branding by custom domain."""
        config = self.manager.get_config_by_domain(domain)
        if config:
            return self.get_branding(config.tenant_id)
        return None
    
    def set_branding(
        self,
        tenant_id: str,
        colors: Optional[Dict[str, str]] = None,
        assets: Optional[Dict[str, str]] = None,
        text: Optional[Dict[str, str]] = None,
        custom_domain: Optional[str] = None,
        features: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """Set branding configuration."""
        # Get existing or create new
        config = self.manager.get_config(tenant_id)
        
        # Update colors
        if colors:
            for key, value in colors.items():
                if hasattr(config.colors, key):
                    setattr(config.colors, key, value)
        
        # Update assets
        if assets:
            for key, value in assets.items():
                snake_key = self._camel_to_snake(key)
                if hasattr(config.assets, snake_key):
                    setattr(config.assets, snake_key, value)
        
        # Update text
        if text:
            for key, value in text.items():
                snake_key = self._camel_to_snake(key)
                if hasattr(config.text, snake_key):
                    setattr(config.text, snake_key, value)
        
        # Update domain
        if custom_domain is not None:
            config.custom_domain = custom_domain
        
        # Update features
        if features:
            config.features.update(features)
        
        # Save
        self.manager.set_config(config)
        
        return {"status": "updated", "tenant_id": tenant_id}
    
    def get_css(self, tenant_id: str) -> str:
        """Get generated CSS for tenant."""
        config = self.manager.get_config(tenant_id)
        return self.css_generator.generate_full_css(config)
    
    def get_css_variables(self, tenant_id: str) -> str:
        """Get CSS variables only."""
        config = self.manager.get_config(tenant_id)
        return self.css_generator.generate_css_variables(config)
    
    def list_tenants(self) -> List[Dict[str, Any]]:
        """List all white-label tenants."""
        return self.manager.list_configs()
    
    def delete_branding(self, tenant_id: str) -> bool:
        """Delete branding configuration."""
        return self.manager.delete_config(tenant_id)
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


# =============================================================================
# Global Service
# =============================================================================

_white_label_service: Optional[WhiteLabelService] = None


def get_white_label_service() -> WhiteLabelService:
    """Get white-label service singleton."""
    global _white_label_service
    if not _white_label_service:
        config_path = os.getenv("WHITE_LABEL_CONFIG", "white_label.yaml")
        _white_label_service = WhiteLabelService(config_path)
    return _white_label_service

