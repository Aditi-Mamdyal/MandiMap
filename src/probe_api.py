import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DATA_GOV_API_KEY")
RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def get_with_retry(params, tries=3, timeout=(10, 120)):
    for attempt in range(1, tries + 1):
        try:
            t0 = time.time()
            r = requests.get(URL, params=params, timeout=timeout)
            print(f"  attempt {attempt}: HTTP {r.status_code} in {time.time() - t0:.1f}s")
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"  attempt {attempt} failed: {type(e).__name__}")
            time.sleep(5 * attempt)
    return None


base = {"api-key": API_KEY, "format": "json", "limit": 5}

print("Test 1: no filter")
data = get_with_retry(base)
if data:
    print("  total:", data.get("total"))
    print("  fields:", [f.get("id") for f in data.get("fields", [])])
    for rec in data.get("records", [])[:3]:
        print("  ", rec)

print("Test 2: filter by state")
data = get_with_retry({**base, "filters[state.keyword]": "Maharashtra"})
if data:
    print("  total:", data.get("total"))