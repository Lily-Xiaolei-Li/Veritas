#!/usr/bin/env python3
"""
Full Integration Test for Veritas Ecosystem
============================================

Tests the integration of:
- Veritas Core (port 8000)
- Scholarly Hollows (plugin loaded in Veritas Core)
- Gnosiplexio (port 8002)

Usage:
    # First start the services:
    docker compose -f docker-compose.integration.yml up --build -d

    # Then run this test:
    python scripts/test_full_integration.py

    # Stop services:
    docker compose -f docker-compose.integration.yml down
"""

import json
import sys
import time
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

# Configuration
VERITAS_CORE_URL = "http://localhost:8000"
GNOSIPLEXIO_URL = "http://localhost:8002"
TIMEOUT = 10  # seconds


class IntegrationTestResult:
    """Test result container."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []
    
    def record_pass(self, test_name: str):
        self.passed += 1
        print(f"  ✅ {test_name}")
    
    def record_fail(self, test_name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {reason}")
        print(f"  ❌ {test_name}: {reason}")
    
    def summary(self) -> bool:
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Integration Test Results: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailed tests:")
            for err in self.errors:
                print(f"  - {err}")
        print(f"{'='*60}\n")
        return self.failed == 0


def http_get(url: str, timeout: int = TIMEOUT) -> Optional[Dict[str, Any]]:
    """Perform HTTP GET and return JSON response."""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as e:
        return None
    except json.JSONDecodeError:
        return None


def http_post(url: str, data: Dict[str, Any], timeout: int = TIMEOUT) -> Optional[Dict[str, Any]]:
    """Perform HTTP POST with JSON body and return response."""
    try:
        body = json.dumps(data).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as e:
        return None
    except json.JSONDecodeError:
        return None


def wait_for_services(max_wait: int = 60) -> bool:
    """Wait for all services to be healthy."""
    print(f"⏳ Waiting for services to be ready (max {max_wait}s)...")
    
    services = [
        ("Veritas Core", f"{VERITAS_CORE_URL}/health"),
        ("Gnosiplexio", f"{GNOSIPLEXIO_URL}/health"),
    ]
    
    start = time.time()
    while time.time() - start < max_wait:
        all_ready = True
        for name, url in services:
            resp = http_get(url, timeout=5)
            if not resp or resp.get("status") != "healthy":
                all_ready = False
                break
        
        if all_ready:
            print("✅ All services ready!\n")
            return True
        
        time.sleep(2)
    
    print("❌ Timeout waiting for services")
    return False


def test_veritas_core_health(result: IntegrationTestResult):
    """Test 1: Veritas Core health check."""
    resp = http_get(f"{VERITAS_CORE_URL}/health")
    
    if resp and resp.get("status") == "healthy":
        result.record_pass("Veritas Core health check")
    else:
        result.record_fail("Veritas Core health check", f"Response: {resp}")


def test_scholarly_hollows_loaded(result: IntegrationTestResult):
    """Test 2: Verify Scholarly Hollows plugin is loaded."""
    resp = http_get(f"{VERITAS_CORE_URL}/api/v1/plugins")
    
    if resp is None:
        result.record_fail("Scholarly Hollows plugin discovery", "No response from /api/v1/plugins")
        return
    
    # Find scholarly-hollows in the list
    sh_plugin = None
    for plugin in resp:
        if plugin.get("name") == "scholarly-hollows":
            sh_plugin = plugin
            break
    
    if sh_plugin is None:
        result.record_fail("Scholarly Hollows plugin discovery", "Plugin not found in list")
        return
    
    if sh_plugin.get("loaded"):
        result.record_pass("Scholarly Hollows plugin loaded")
    else:
        result.record_fail("Scholarly Hollows plugin loaded", "Plugin found but not loaded")


def test_scholarly_hollows_health(result: IntegrationTestResult):
    """Test 3: Scholarly Hollows health endpoint."""
    resp = http_get(f"{VERITAS_CORE_URL}/api/v1/sh/health")
    
    if resp and resp.get("status") in ("ok", "degraded"):
        spells = resp.get("spells", [])
        failed = resp.get("failed", [])
        
        if len(spells) > 0:
            result.record_pass(f"Scholarly Hollows health ({len(spells)} spells loaded)")
            if failed:
                print(f"      ⚠️  {len(failed)} spells failed to load (dependencies missing)")
        elif resp.get("status") == "degraded":
            result.record_pass(f"Scholarly Hollows health (degraded mode)")
        else:
            result.record_fail("Scholarly Hollows spells", f"No spells loaded: {resp}")
    else:
        result.record_fail("Scholarly Hollows health", f"Response: {resp}")


def test_gnosiplexio_health(result: IntegrationTestResult):
    """Test 4: Gnosiplexio health check."""
    resp = http_get(f"{GNOSIPLEXIO_URL}/health")
    
    if resp and resp.get("status") == "healthy":
        config = resp.get("config", {})
        data_source = config.get("data_source", "")
        veritas_url = config.get("veritas_api_url", "")
        
        if data_source == "veritas" and "veritas-core" in veritas_url:
            result.record_pass(f"Gnosiplexio health (source: {data_source})")
        else:
            result.record_fail(
                "Gnosiplexio health",
                f"Unexpected config: source={data_source}, url={veritas_url}"
            )
    else:
        result.record_fail("Gnosiplexio health", f"Response: {resp}")


def test_gnosiplexio_stats(result: IntegrationTestResult):
    """Test 5: Gnosiplexio graph stats endpoint."""
    resp = http_get(f"{GNOSIPLEXIO_URL}/api/v1/gnosiplexio/stats")
    
    if resp is not None and "total_nodes" in resp:
        result.record_pass(f"Gnosiplexio stats (nodes: {resp.get('total_nodes', 0)})")
    else:
        result.record_fail("Gnosiplexio stats", f"Response: {resp}")


def test_gnosiplexio_ingest_inline(result: IntegrationTestResult):
    """Test 6: Gnosiplexio inline data ingestion."""
    test_paper = {
        "id": "test-paper-001",
        "title": "Integration Test Paper",
        "authors": ["Test Author"],
        "year": 2024,
        "abstract": "This is a test paper for integration testing.",
        "doi": "10.1234/test.001",
    }
    
    resp = http_post(
        f"{GNOSIPLEXIO_URL}/api/v1/gnosiplexio/ingest",
        {"data": json.dumps(test_paper)},
    )
    
    if resp and resp.get("node_id"):
        result.record_pass(f"Gnosiplexio ingest (node: {resp.get('node_id')})")
    else:
        result.record_fail("Gnosiplexio ingest", f"Response: {resp}")


def test_gnosiplexio_search(result: IntegrationTestResult):
    """Test 7: Gnosiplexio search."""
    resp = http_get(f"{GNOSIPLEXIO_URL}/api/v1/gnosiplexio/search?q=test")
    
    if resp is not None and "results" in resp:
        result.record_pass(f"Gnosiplexio search (results: {resp.get('total', 0)})")
    else:
        result.record_fail("Gnosiplexio search", f"Response: {resp}")


def test_gnosiplexio_export(result: IntegrationTestResult):
    """Test 8: Gnosiplexio graph export."""
    resp = http_get(f"{GNOSIPLEXIO_URL}/api/v1/gnosiplexio/graph?format=json")
    
    if resp and "nodes" in resp and "edges" in resp:
        nodes = len(resp.get("nodes", []))
        edges = len(resp.get("edges", []))
        result.record_pass(f"Gnosiplexio export (nodes: {nodes}, edges: {edges})")
    else:
        result.record_fail("Gnosiplexio export", f"Response: {resp}")


def test_scholarly_hollows_spell(result: IntegrationTestResult):
    """Test 9: Scholarly Hollows spell invocation."""
    # First check which spells are available
    health_resp = http_get(f"{VERITAS_CORE_URL}/api/v1/sh/health")
    loaded_spells = health_resp.get("spells", []) if health_resp else []
    
    if "veritafactum" in loaded_spells:
        # Try veritafactum checker
        resp = http_post(
            f"{VERITAS_CORE_URL}/api/v1/sh/checker/run",
            {"text": "This is a test sentence that needs verification."},
        )
        
        if resp and resp.get("run_id"):
            run_id = resp.get("run_id")
            status = resp.get("status")
            result.record_pass(f"Veritafactum spell (run_id: {run_id}, status: {status})")
        else:
            result.record_fail("Veritafactum spell", f"Response: {resp}")
    elif "exportario" in loaded_spells:
        # Try exportario status (simpler endpoint)
        resp = http_get(f"{VERITAS_CORE_URL}/api/v1/sh/exportario/status")
        
        if resp and resp.get("spell") == "exportario":
            result.record_pass(f"Ex-portario spell (status: {resp.get('status')})")
        else:
            result.record_fail("Ex-portario spell", f"Response: {resp}")
    else:
        # No spells available - test /spells endpoint instead
        resp = http_get(f"{VERITAS_CORE_URL}/api/v1/sh/spells")
        
        if resp and "spells" in resp:
            total = resp.get("total", 0)
            loaded = resp.get("loaded", 0)
            result.record_pass(f"Scholarly Hollows /spells endpoint ({loaded}/{total} loaded)")
        else:
            result.record_fail("Scholarly Hollows spell", "No spells available and /spells endpoint failed")


def test_cross_service_communication(result: IntegrationTestResult):
    """Test 10: Cross-service communication (GP → Veritas)."""
    # Gnosiplexio should be configured to talk to Veritas Core
    # We verify this by checking the health endpoint config
    resp = http_get(f"{GNOSIPLEXIO_URL}/health")
    
    if resp:
        config = resp.get("config", {})
        veritas_url = config.get("veritas_api_url", "")
        
        # Verify the URL points to veritas-core (Docker internal network)
        if "veritas-core:8000" in veritas_url or "localhost:8000" in veritas_url:
            result.record_pass("Cross-service communication configured")
        else:
            result.record_fail(
                "Cross-service communication",
                f"Veritas URL not configured correctly: {veritas_url}"
            )
    else:
        result.record_fail("Cross-service communication", "Could not get GP health")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Veritas Ecosystem Integration Tests")
    print("=" * 60)
    print(f"Veritas Core: {VERITAS_CORE_URL}")
    print(f"Gnosiplexio:  {GNOSIPLEXIO_URL}")
    print()
    
    # Wait for services
    if not wait_for_services():
        print("\n⚠️  Services not ready. Make sure to run:")
        print("   docker compose -f docker-compose.integration.yml up --build -d")
        sys.exit(1)
    
    # Run tests
    result = IntegrationTestResult()
    
    print("Running integration tests...\n")
    
    # Group 1: Health checks
    print("📋 Health Checks:")
    test_veritas_core_health(result)
    test_gnosiplexio_health(result)
    
    # Group 2: Plugin system
    print("\n🔌 Plugin System:")
    test_scholarly_hollows_loaded(result)
    test_scholarly_hollows_health(result)
    
    # Group 3: Gnosiplexio functionality
    print("\n📊 Gnosiplexio Features:")
    test_gnosiplexio_stats(result)
    test_gnosiplexio_ingest_inline(result)
    test_gnosiplexio_search(result)
    test_gnosiplexio_export(result)
    
    # Group 4: Scholarly Hollows spells
    print("\n✨ Scholarly Hollows Spells:")
    test_scholarly_hollows_spell(result)
    
    # Group 5: Integration
    print("\n🔗 Cross-Service Integration:")
    test_cross_service_communication(result)
    
    # Summary
    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
