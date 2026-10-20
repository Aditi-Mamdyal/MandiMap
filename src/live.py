import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from clean import clean_frame

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT / "data" / "processed" / "live_history.csv"
KEY = ["date", "market", "commodity"]
API_KEY = os.getenv("DATA_GOV_API_KEY")
# Current Daily Price of Various Commodities from Various Markets (Mandi)
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
PAGE = 1000

# data.gov.in's gateway returns 502 for the default python-requests User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

# Some OGD resources use these older field names; map them to the ones clean.py expects
FIELD_FIXES = {"min_x0020_price": "min_price", "max_x0020_price": "max_price",
               "modal_x0020_price": "modal_price"}


def _get(params, tries=3, timeout=(10, 120)):
    """GET with retry. Errors are re-raised WITHOUT the URL, because the URL contains the API key."""
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(URL, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt == tries:
                status = getattr(e.response, "status_code", None)
                what = f"HTTP {status}" if status else type(e).__name__
                raise RuntimeError(f"data.gov.in request failed ({what})") from None
            time.sleep(5 * attempt)


def fetch_recent_pune() -> pd.DataFrame:
    """Pune records currently published by the daily-price resource (latest reporting day(s))."""
    if not API_KEY:
        raise RuntimeError("DATA_GOV_API_KEY is missing. Add it to your .env file.")
    params = {
        "api-key": API_KEY, "format": "json", "limit": PAGE, "offset": 0,
        "filters[state.keyword]": "Maharashtra",
        "filters[district]": "Pune",
    }
    rows = []
    while True:
        batch = _get(params).get("records", [])
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        params["offset"] += PAGE

    df = pd.DataFrame(rows)
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]
        df = df.rename(columns=FIELD_FIXES)
    return df


def update_history(live_raw: pd.DataFrame) -> int:
    """Clean the live rows and save them into live_history.csv. New days are added;
    a day fetched again (e.g. a partial day completed later) is replaced. Returns rows saved."""
    if live_raw is None or live_raw.empty:
        return 0
    daily, _, _ = clean_frame(live_raw)
    daily["date"] = pd.to_datetime(daily["date"])
    if HISTORY_FILE.exists():
        daily = pd.concat([pd.read_csv(HISTORY_FILE, parse_dates=["date"]), daily], ignore_index=True)
    daily = daily.drop_duplicates(subset=KEY, keep="last").sort_values(KEY)
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(HISTORY_FILE, index=False)
    return len(daily)


def add_history(clean_df: pd.DataFrame) -> pd.DataFrame:
    """clean.csv data + everything saved in live_history.csv (history file wins on overlap)."""
    if not HISTORY_FILE.exists():
        return clean_df
    hist = pd.read_csv(HISTORY_FILE, parse_dates=["date"])
    out = pd.concat([clean_df, hist], ignore_index=True).drop_duplicates(subset=KEY, keep="last")
    return out.sort_values(KEY).reset_index(drop=True)


def merge_live(clean_df: pd.DataFrame, live_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean the live rows like the CSV rows and add them to clean.csv's data.
    Where a day/market/crop exists in both, the live version wins."""
    if live_raw is None or live_raw.empty:
        return clean_df
    live_daily, _, _ = clean_frame(live_raw)
    live_daily["date"] = pd.to_datetime(live_daily["date"])
    out = pd.concat([clean_df, live_daily], ignore_index=True)
    out = out.drop_duplicates(subset=["date", "market", "commodity"], keep="last")
    return out.sort_values(["date", "market", "commodity"]).reset_index(drop=True)


if __name__ == "__main__":          # self-test: python src/live.py
    df = fetch_recent_pune()
    print("rows:", len(df))
    print("columns:", list(df.columns))
    if not df.empty:
        print("saved to live_history.csv, total rows there:", update_history(df))
        print("dates:", sorted(df["arrival_date"].unique()))
        print(df.head().to_string())