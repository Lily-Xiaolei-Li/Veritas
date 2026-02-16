"""Download Elsevier PDFs via authenticated Chrome browser using CDP."""
import json
import time
import urllib.request
import base64
from pathlib import Path

CDP_URL = "http://127.0.0.1:9222"
OUTPUT_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend\data\downloads\knowledge")

PAPERS = [
    ("10.1016/j.jaccpubpol.2026.107406", "Maroun_2026_Framing_UK_audit_regulator"),
    ("10.1016/j.jbusres.2025.115376", "Leger_2025_Enabling_social_identity_work"),
    ("10.1016/j.jbusres.2025.115482", "Zhao_2025_Dual_effects_AI_job"),
    ("10.1016/j.jclepro.2022.134725", "Misslin_2022_Integrated_assessment_recycling"),
    ("10.1016/j.jenvman.2025.127828", "Zhao_2025_Pathways_green_development"),
    ("10.1016/j.labeco.2025.102765", "Kudlyak_2025_Minimum_wage_vacancies"),
    ("10.1016/j.pacfin.2025.102946", "Yao_2025_Multi_factor_portfolio"),
    ("10.1016/j.respol.2025.105292", "Vedel_2025_Organizing_transformative_innovation"),
    ("10.1016/j.ribaf.2025.103031", "Zhuang_2025_ESG_sentiment_risk"),
    ("10.1016/j.ribaf.2025.103147", "Setianto_2025_Financial_inclusion_risk"),
    ("10.1016/j.rie.2025.101057", "Huy_2025_Blockchain_auditing_SDG8"),
    ("10.1016/j.rser.2025.116282", "Sun_2026_Renewable_energy_hot_water"),
    ("10.1016/j.techfore.2025.124414", "Zhang_2026_Digital_govt_carbon"),
    ("10.1016/j.tre.2025.104446", "Sun_2025_ESG_operational_efficiency"),
]

def get_ws_url(target_id):
    """Get WebSocket URL for a target."""
    req = urllib.request.Request(f"{CDP_URL}/json/list")
    with urllib.request.urlopen(req, timeout=10) as resp:
        targets = json.loads(resp.read())
    for t in targets:
        if t.get("id") == target_id:
            return t.get("webSocketDebuggerUrl")
    return None

def navigate_and_get_pdf_url(target_id, doi):
    """Navigate to DOI via EZProxy and extract pdfft link."""
    import websocket
    ws_url = get_ws_url(target_id)
    if not ws_url:
        return None
    
    ws = websocket.create_connection(ws_url, timeout=30)
    
    # Navigate
    ezproxy_url = f"https://doi-org.ezproxy.newcastle.edu.au/{doi}"
    ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": ezproxy_url}}))
    ws.recv()  # ack
    
    # Wait for load
    time.sleep(6)
    
    # Extract pdfft link
    js = "document.querySelector(\"a[href*='pdfft']\") ? document.querySelector(\"a[href*='pdfft']\").href : null"
    ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {"expression": js}}))
    result = json.loads(ws.recv())
    pdf_url = result.get("result", {}).get("result", {}).get("value")
    
    ws.close()
    return pdf_url

def download_pdf_via_fetch(target_id, pdf_url):
    """Use browser's fetch to download PDF as base64."""
    import websocket
    ws_url = get_ws_url(target_id)
    if not ws_url:
        return None
    
    ws = websocket.create_connection(ws_url, timeout=120)
    
    # Navigate to the article page first (same origin)
    # Then fetch the PDF
    js = f"""
    (async () => {{
        try {{
            const resp = await fetch("{pdf_url}");
            const blob = await resp.blob();
            return new Promise((resolve) => {{
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            }});
        }} catch(e) {{
            return "ERROR:" + e.message;
        }}
    }})()
    """
    
    ws.send(json.dumps({
        "id": 3, 
        "method": "Runtime.evaluate", 
        "params": {"expression": js, "awaitPromise": True, "timeout": 60000}
    }))
    
    result = json.loads(ws.recv())
    data_url = result.get("result", {}).get("result", {}).get("value", "")
    ws.close()
    
    if data_url and data_url.startswith("data:"):
        # Extract base64 from data URL
        b64 = data_url.split(",", 1)[1] if "," in data_url else ""
        return base64.b64decode(b64)
    return None

# Main
print(f"Downloading {len(PAPERS)} papers via EZProxy browser")

# Get first available page target
req = urllib.request.Request(f"{CDP_URL}/json/list")
with urllib.request.urlopen(req, timeout=10) as resp:
    targets = json.loads(resp.read())

page_targets = [t for t in targets if t.get("type") == "page"]
if not page_targets:
    print("ERROR: No Chrome page targets found!")
    exit(1)

target_id = page_targets[0]["id"]
print(f"Using target: {target_id}")

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    import subprocess
    subprocess.check_call(["pip", "install", "websocket-client"])
    import websocket

ok = 0
fail = 0
for i, (doi, name) in enumerate(PAPERS):
    print(f"\n[{i+1}/{len(PAPERS)}] {doi}")
    out_file = OUTPUT_DIR / f"{name}.pdf"
    
    # Navigate to article and get PDF URL
    pdf_url = navigate_and_get_pdf_url(target_id, doi)
    if not pdf_url:
        print(f"  ERROR: Could not find pdfft link")
        fail += 1
        continue
    print(f"  PDF URL: {pdf_url[:80]}...")
    
    # Download PDF via browser fetch (same origin, has cookies)
    pdf_bytes = download_pdf_via_fetch(target_id, pdf_url)
    if not pdf_bytes or len(pdf_bytes) < 10000:
        print(f"  ERROR: Download failed or too small ({len(pdf_bytes) if pdf_bytes else 0} bytes)")
        fail += 1
        continue
    
    # Verify it's a real PDF
    if not pdf_bytes[:5] == b"%PDF-":
        print(f"  ERROR: Not a valid PDF (header: {pdf_bytes[:20]})")
        fail += 1
        continue
    
    out_file.write_bytes(pdf_bytes)
    print(f"  OK: {len(pdf_bytes)} bytes -> {out_file.name}")
    ok += 1
    
    time.sleep(2)  # Rate limit

print(f"\n{'='*50}")
print(f"Done: {ok} OK, {fail} failed out of {len(PAPERS)}")
