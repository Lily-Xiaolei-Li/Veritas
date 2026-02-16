import httpx, json

dois = ["10.3390/su13031309", "10.1371/journal.pone.0159050", "10.1016/j.jaccpubpol.2026.107406"]
email = "lily.xiaolei.li@outlook.com"

for doi in dois:
    r = httpx.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": email}, timeout=15)
    if r.status_code == 200:
        data = r.json()
        oa = data.get("best_oa_location") or {}
        print(f"DOI: {doi}")
        print(f"  is_oa: {data.get('is_oa')}")
        print(f"  pdf_url: {oa.get('url_for_pdf', 'None')}")
        print(f"  host: {oa.get('host_type', '?')}")
    else:
        print(f"DOI: {doi} → HTTP {r.status_code}")
    print()
