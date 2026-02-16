"""Test the new paper downloader directly."""
import asyncio
import sys
sys.path.insert(0, "backend")

from app.services.knowledge_source.paper_downloader import PaperDownloader

async def main():
    dl = PaperDownloader()
    
    # Test 1: Known OA paper (MDPI)
    print("=== Test 1: MDPI OA Paper ===")
    r1 = await dl.download(doi="10.3390/su13031309")
    print(f"  Status: {r1.get('status')}")
    print(f"  Source: {r1.get('source')}")
    print(f"  File: {r1.get('file_path', '')[:80]}")
    print(f"  Needs proxy: {r1.get('needs_proxy')}")
    if r1.get('error'):
        print(f"  Error: {r1.get('error')}")
    
    # Test 2: Elsevier paywall
    print("\n=== Test 2: Elsevier Paywall ===")
    r2 = await dl.download(doi="10.1016/j.jaccpubpol.2026.107406")
    print(f"  Status: {r2.get('status')}")
    print(f"  Source: {r2.get('source')}")
    print(f"  Needs proxy: {r2.get('needs_proxy')}")
    print(f"  Proxy URL: {r2.get('proxy_url', '')[:80]}")
    
    # Test 3: Another known OA (PLoS ONE)
    print("\n=== Test 3: PLoS ONE OA ===")
    r3 = await dl.download(doi="10.1371/journal.pone.0159050")
    print(f"  Status: {r3.get('status')}")
    print(f"  Source: {r3.get('source')}")
    print(f"  File: {r3.get('file_path', '')[:80]}")
    if r3.get('error'):
        print(f"  Error: {r3.get('error')}")

asyncio.run(main())
