"""Manual API smoke script.

NOTE: This file is *not* part of the automated pytest suite.
Run it manually if you want a quick local check.

    python test_api.py

"""

# Tell pytest to ignore this module
__test__ = False

# Set environment before imports
import os

from fastapi.testclient import TestClient

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://agentb:AgentB#Lily2026!@localhost:5433/agent_b'
os.environ['AUTH_ENABLED'] = 'false'

from app.main import app

client = TestClient(app)

def test_sessions():
    print("Testing /api/v1/sessions...")
    response = client.get("/api/v1/sessions")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text[:500] if response.text else 'Empty'}")

def test_health():
    print("Testing /health...")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text[:500] if response.text else 'Empty'}")

if __name__ == "__main__":
    test_health()
    print()
    test_sessions()
