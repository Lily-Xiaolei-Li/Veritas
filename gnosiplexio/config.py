"""
Gnosiplexio Configuration — Environment-based settings.
"""
from __future__ import annotations

import os
from typing import Literal

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
    
    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]
    
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
