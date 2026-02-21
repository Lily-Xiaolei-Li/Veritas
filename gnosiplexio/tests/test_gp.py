"""
Gnosiplexio Integration Tests
"""
import pytest

def test_adapter_imports():
    from adapters.base import DataSourceAdapter
    from adapters.veritas_adapter import VeritasAdapter
    assert DataSourceAdapter is not None
    assert VeritasAdapter is not None

def test_config():
    from config import get_settings
    settings = get_settings()
    assert settings.DATA_SOURCE in ["veritas", "generic"]
    assert settings.VERITAS_API_URL is not None

def test_veritas_adapter_init():
    from adapters.veritas_adapter import VeritasAdapter
    adapter = VeritasAdapter(base_url="http://test:8001")
    assert adapter.base_url == "http://test:8001"
