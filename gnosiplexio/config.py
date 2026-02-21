"""
Gnosiplexio Configuration — Environment-based settings.
"""
from __future__ import annotations

import os
from typing import Literal, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


class GnosiplexioSettings(BaseSettings):
    """
    Gnosiplexio configuration settings.
    
    Environment variables:
      - GNOSIPLEXIO_DATA_SOURCE: "veritas" or "generic" (default: veritas)
      - GNOSIPLEXIO_VERITAS_API_URL: URL for Veritas API (default: http://localhost:8001)
      - GNOSIPLEXIO_DATA_DIR: Directory for graph persistence (default: data/gnosiplexio)
      - GNOSIPLEXIO_AUTO_SAVE: Auto-save graph on changes (default: true)
    """
    
    # Data source adapter selection
    DATA_SOURCE: Literal["veritas", "generic"] = "veritas"
    
    # Veritas API connection
    VERITAS_API_URL: str = "http://localhost:8001"
    
    # Graph persistence
    DATA_DIR: str = "data/gnosiplexio"
    AUTO_SAVE: bool = True
    
    # CORS settings (accepts string or list)
    CORS_ORIGINS: list[str] = ["*"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string or list."""
        if isinstance(v, str):
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    model_config = {
        "env_prefix": "GNOSIPLEXIO_",
        "env_file": ".env",
        "extra": "ignore",
    }


# Singleton settings instance
_settings: GnosiplexioSettings | None = None


def get_settings() -> GnosiplexioSettings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = GnosiplexioSettings()
    return _settings
