"""Test sync with a known paper: Power 2015"""
import json
from pathlib import Path
from qdrant_client import QdrantClient
import httpx

LIBRARY_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")
GATEWAY_URL = "http://localhost:18789"
GATEWAY_TOKEN = "cf8bf99bedae98b1c3feea260670dcb023a0dfb04fddf379"

# Find Power 2015 in library
power_file = None
for f in LIBRARY_PATH.glob("Power_2015*.md"):
    power_file = f
    break

if not power_file:
    print("Power 2015 not found in library!")
    exit(1)

print(f"Found: {power_file.name}")

# Read first 1000 chars
content = power_file.read_text(encoding='utf-8', errors='ignore')[:1000]
print(f"\nFirst 500 chars:\n{content[:500]}")

# Extract with AI
print("\n--- AI Extraction ---")
headers = {
    "Authorization": f"Bearer {GATEWAY_TOKEN}",
    "Content-Type": "application/json",
    "x-openclaw-agent-id": "coder"
}
payload = {
    "model": "coder",
    "messages": [{"role": "user", "content": f'''Extract metadata from this academic paper. Return ONLY valid JSON.

{content}

Return: {{"authors": ["Name"], "year": 2024, "journal": "Name"}}'''}],
    "temperature": 0,
    "max_tokens": 300
}

with httpx.Client(timeout=60) as client:
    resp = client.post(f"{GATEWAY_URL}/v1/chat/completions", headers=headers, json=payload)
    data = resp.json()
    ai_result = data["choices"][0]["message"]["content"]
    print(f"AI result: {ai_result}")

# Check VF store for Power 2015
print("\n--- VF Store Check ---")
c = QdrantClient(host='localhost', port=6333)
results, _ = c.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=100, with_payload=['meta', 'paper_id'])

for p in results:
    meta = p.payload.get('meta', {})
    if meta.get('year') == 2015:
        authors = meta.get('authors', [])
        if any('power' in str(a).lower() for a in authors):
            print(f"Found in VF: paper_id={p.payload.get('paper_id')}")
            print(f"  title: {meta.get('title')}")
            print(f"  authors: {authors}")
            print(f"  year: {meta.get('year')}")
            print(f"  journal: {meta.get('journal')}")
