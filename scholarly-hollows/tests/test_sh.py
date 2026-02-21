"""
Scholarly Hollows Plugin Tests
"""
import pytest

def test_router_import():
    from routes import router
    assert router is not None

def test_manifest_valid():
    import json
    from pathlib import Path
    manifest_path = Path(__file__).parent.parent / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert manifest["name"] == "scholarly-hollows"
    assert len(manifest["spells"]) == 4

def test_all_spell_routers():
    from routes.veritafactum import router as vf
    from routes.citalio import router as ct
    from routes.proliferomaxima import router as pm
    from routes.exportario import router as ex
    assert all([vf, ct, pm, ex])
