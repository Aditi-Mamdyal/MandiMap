import os
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("DATA_GOV_API_KEY")
URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}
ST = {"filters[state.keyword]": "Maharashtra"}
DI = {"filters[district]": "Pune"}

tests = [
    ("A  limit=5, no filters, default UA",       {"limit": 5}, None),
    ("B  limit=5, no filters, browser UA",       {"limit": 5}, BROWSER),
    ("C  limit=5 + state.keyword",               {"limit": 5, **ST}, BROWSER),
    ("D  limit=5 + state (no .keyword)",         {"limit": 5, "filters[state]": "Maharashtra"}, BROWSER),
    ("E  limit=5 + state.keyword + district",    {"limit": 5, **ST, **DI}, BROWSER),
    ("F  limit=100 + state.keyword + district",  {"limit": 100, **ST, **DI}, BROWSER),
    ("G  limit=1000 + state.keyword + district", {"limit": 1000, **ST, **DI}, BROWSER),
]

if not KEY:
    raise SystemExit("DATA_GOV_API_KEY missing in .env")

for name, extra, headers in tests:
    params = {"api-key": KEY, "format": "json", **extra}
    try:
        r = requests.get(URL, params=params, headers=headers, timeout=(10, 120))
        info = f"HTTP {r.status_code}"
        if r.ok:
            j = r.json()
            info += f" | records={len(j.get('records', []))} total={j.get('total')}"
    except requests.RequestException as e:
        info = type(e).__name__
    print(f"{name:45s} {info}")