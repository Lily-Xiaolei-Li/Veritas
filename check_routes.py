import requests
r = requests.get("http://localhost:8001/openapi.json")
data = r.json()
for path in sorted(data.get("paths", {}).keys()):
    if "knowledge" in path or "vf" in path:
        methods = list(data["paths"][path].keys())
        print(f"{','.join(methods):10s} {path}")
