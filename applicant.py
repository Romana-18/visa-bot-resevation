# save as probe_common_paths.py then:  python probe_common_paths.py https://egy.almaviva-visa.it
import requests, sys
from urllib.parse import urljoin

ROOT = sys.argv[1]
paths = [
  "/openapi.json","/swagger.json","/swagger","/swagger-ui.html","/v3/api-docs",
  "/api-docs","/docs","/redoc","/api/status","/status","/health","/api/health",
  "/graphql","/api/","/api/v1/","/config.json","/assets/config.json","/app-config.json",
  "/cms","/wp-json"
]
for p in paths:
    url = urljoin(ROOT, p)
    try:
        r = requests.get(url, timeout=8, headers={"Accept":"application/json"})
        if r.status_code < 400:
            print(f"[+] {url}  {r.status_code}  {r.headers.get('content-type','')}")
            print((r.text[:400]+"\n----"))
    except requests.RequestException:
        pass
