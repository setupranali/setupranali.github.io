"""
Configuration Management

Centralized configuration using Pydantic Settings.
"""

import os
from typing import Optional

# Try to import BaseSettings - handle both Pydantic v1 and v2
try:
    # Pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import Field
    PYDANTIC_V2 = True
except ImportError:
    try:
        # Pydantic v1
        from pydantic import BaseSettings, Field
        PYDANTIC_V2 = False
    except ImportError:
        # Fallback - use environment variables directly
        BaseSettings = None
        Field = None
        PYDANTIC_V2 = False


if BaseSettings is not None:
    class Settings(BaseSettings):
        """Application settings."""
        
        # Application
        app_name: str = "SetuPranali"
        app_version: str = "1.0.0"
        environment: str = Field(default="development", env="ENV")
        debug: bool = Field(default=False, env="DEBUG")
        
        # Security
        secret_key: Optional[str] = Field(default=None, env="UBI_SECRET_KEY")
        api_key_header: str = "X-API-Key"
        
        # Database
        redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
        cache_enabled: bool = Field(default=False, env="CACHE_ENABLED")
        
        # Observability
        analytics_enabled: bool = Field(default=True, env="ANALYTICS_ENABLED")
        analytics_retention_hours: int = Field(default=168, env="ANALYTICS_RETENTION_HOURS")
        
        # Rate Limiting
        rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
        rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
        
        class Config:
            env_file = ".env"
            case_sensitive = False
else:
    # Fallback class if Pydantic is not available
    class Settings:
        def __init__(self):
            self.app_name = os.getenv("APP_NAME", "SetuPranali")
            self.app_version = os.getenv("APP_VERSION", "1.0.0")
            self.environment = os.getenv("ENV", "development")
            self.debug = os.getenv("DEBUG", "false").lower() == "true"
            self.secret_key = os.getenv("UBI_SECRET_KEY")
            self.api_key_header = "X-API-Key"
            self.redis_url = os.getenv("REDIS_URL")
            self.cache_enabled = os.getenv("CACHE_ENABLED", "false").lower() == "true"
            self.analytics_enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
            self.analytics_retention_hours = int(os.getenv("ANALYTICS_RETENTION_HOURS", "168"))
            self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
            self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


# Global settings instance
settings = Settings()
