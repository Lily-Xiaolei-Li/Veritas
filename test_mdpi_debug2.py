import urllib.request

url = "https://www.mdpi.com/2071-1050/13/3/1309/pdf?version=1612421556"
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

try:
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(200)
        print(f"Status: {resp.status}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"Is PDF: {data.startswith(b'%PDF')}")
        print(f"Size so far: {len(data)}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
