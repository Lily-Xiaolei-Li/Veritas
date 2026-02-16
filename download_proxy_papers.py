"""Download paywalled papers via EZProxy-authenticated Chrome browser."""
import json
import time
import urllib.request
import os
import re

DOIS = [
    "10.1016/j.jaccpubpol.2026.107406",
    "10.1016/j.jbusres.2025.115376",
    "10.1016/j.jbusres.2025.115482",
    "10.1016/j.jclepro.2022.134725",
    "10.1016/j.jenvman.2025.127828",
    "10.1016/j.labeco.2025.102765",
    "10.1016/j.pacfin.2025.102946",
    "10.1016/j.respol.2025.105292",
    "10.1016/j.ribaf.2025.103031",
    "10.1016/j.ribaf.2025.103147",
    "10.1016/j.rie.2025.101057",
    "10.1016/j.rser.2025.116282",
    "10.1016/j.techfore.2025.124414",
    "10.1016/j.tre.2025.104446",
]

CDP_URL = "http://127.0.0.1:9222"
OUTPUT_DIR = r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend\data\downloads\knowledge"
EZPROXY_TEMPLATE = "https://ezproxy.newcastle.edu.au/login?url=https://doi.org/{doi}"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def cdp_send(ws_url, method, params=None):
    """Send CDP command via HTTP endpoint (simplified - we'll use the page targets)."""
    pass

def get_targets():
    """Get list of Chrome tabs."""
    req = urllib.request.Request(f"{CDP_URL}/json/list")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def find_pdf_link_in_page(page_url):
    """For ScienceDirect pages, construct the PDF URL from the PII."""
    # Extract PII from URL
    m = re.search(r'/pii/(\w+)', page_url)
    if m:
        pii = m.group(1)
        return f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft"
    return None

print(f"Will download {len(DOIS)} papers via EZProxy")
print(f"Output: {OUTPUT_DIR}")
print()

# Since browser is already authenticated with EZProxy, 
# we can construct proxied PDF URLs directly
results = []
for i, doi in enumerate(DOIS):
    print(f"[{i+1}/{len(DOIS)}] {doi}")
    
    # Construct EZProxy-proxied ScienceDirect PDF URL
    # EZProxy rewrites: sciencedirect.com -> sciencedirect-com.ezproxy.newcastle.edu.au
    safe_doi = doi.replace("/", "%2F")
    
    # First resolve DOI to get the PII
    try:
        req = urllib.request.Request(
            f"https://doi.org/{doi}",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
        )
        req.get_method = lambda: "HEAD"
        # Follow redirects to get final URL
        import urllib.request as ur
        opener = ur.build_opener(ur.HTTPRedirectHandler)
        resp = opener.open(req, timeout=15)
        final_url = resp.url
        print(f"  Resolved to: {final_url}")
        
        # Extract PII from ScienceDirect URL
        m = re.search(r'/pii/(\w+)', final_url)
        if m:
            pii = m.group(1)
            # Construct EZProxy PDF URL
            pdf_url = f"https://www-sciencedirect-com.ezproxy.newcastle.edu.au/science/article/pii/{pii}/pdfft?md5=&pid=1-s2.0-{pii}-main.pdf"
            print(f"  PDF URL: {pdf_url}")
            results.append({"doi": doi, "pii": pii, "pdf_url": pdf_url, "status": "ready"})
        else:
            print(f"  WARNING: No PII found in URL")
            results.append({"doi": doi, "final_url": final_url, "status": "no_pii"})
    except Exception as e:
        print(f"  ERROR resolving DOI: {e}")
        results.append({"doi": doi, "status": "error", "error": str(e)})
    
    time.sleep(1)  # Rate limit

# Save results for browser download
out_file = os.path.join(OUTPUT_DIR, "proxy_download_urls.json")
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved {len(results)} URLs to {out_file}")
print(f"Ready URLs: {sum(1 for r in results if r.get('status') == 'ready')}")
