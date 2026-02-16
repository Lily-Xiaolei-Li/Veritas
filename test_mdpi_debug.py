import urllib.request, json

url = "https://www.mdpi.com/2071-1050/13/3/1309/pdf?version=1612421556"
ua = "AgentB-Knowledge/2.0 (mailto:lily.xiaolei.li@outlook.com)"

try:
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "application/pdf,*/*",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        ct = resp.headers.get("Content-Type", "")
        fu = resp.geturl()
        data = resp.read(100)
        print(f"Status: {resp.status}")
        print(f"Content-Type: {ct}")
        print(f"Final URL: {fu}")
        print(f"First 50 bytes: {data[:50]}")
        print(f"Is PDF: {data.startswith(b'%PDF')}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
