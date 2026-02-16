"""Test multiple OA papers to see download success rate."""
import asyncio, sys
sys.path.insert(0, "backend")
from app.services.knowledge_source.paper_downloader import PaperDownloader

# Mix of publishers
test_dois = [
    ("10.1371/journal.pone.0159050", "PLoS ONE"),
    ("10.3389/fpsyg.2022.851710", "Frontiers"),
    ("10.7717/peerj.13612", "PeerJ"),
    ("10.1186/s12913-022-08536-0", "BMC/Springer"),
    ("10.3390/su13031309", "MDPI"),
]

async def main():
    dl = PaperDownloader()
    success = 0
    for doi, pub in test_dois:
        r = await dl.download(doi=doi)
        status = r.get("status")
        source = r.get("source", "?")
        ok = "✅" if status == "success" else "❌"
        if status == "success":
            success += 1
        print(f"  {ok} [{pub:12s}] {doi} → {source}")
    print(f"\nTotal: {success}/{len(test_dois)} downloaded")

asyncio.run(main())
