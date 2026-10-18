import io
import re
from pathlib import Path

import pandas as pd

from config import MARKET_ALIASES, MARKET_TALUKA

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / "mandimapcsv.csv"   # change to your file name
OUT_FILE = ROOT / "data" / "processed" / "clean.csv"


def load_raw(path: Path) -> pd.DataFrame:
    """Load CSV or Excel. Handles CSVs where every row is wrapped in quotes."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    df = pd.read_csv(path, encoding="utf-8-sig")
    if df.shape[1] == 1:  # whole row ended up in one column
        text = path.read_text(encoding="utf-8-sig")
        lines = [l.strip().strip('"') for l in text.splitlines() if l.strip()]
        df = pd.read_csv(io.StringIO("\n".join(lines)))
    return df


def normalize_market(name: str) -> str:
    s = re.sub(r"\bAPMC\b", "", str(name), flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return MARKET_ALIASES.get(s, s)


def main():
    df = load_raw(RAW_FILE)
    report = {"raw rows": len(df)}

    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"arrival_date": "date"})

    # Dates (dd/mm/yyyy)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    report["after valid dates"] = len(df)

    # Text columns
    for col in ["state", "district", "commodity", "market"]:
        df[col] = df[col].astype(str).str.strip()
    df = df[df["state"].str.lower() == "maharashtra"]
    report["after Maharashtra filter"] = len(df)

    # Prices
    for col in ["min_price", "max_price", "modal_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["min_price", "max_price", "modal_price"])
    df = df[(df[["min_price", "max_price", "modal_price"]] > 0).all(axis=1)]
    df = df[df["min_price"] <= df["max_price"]]
    df = df[(df["modal_price"] >= df["min_price"]) & (df["modal_price"] <= df["max_price"])]
    report["after price checks"] = len(df)

    # Exact duplicates
    df = df.drop_duplicates()
    report["after removing exact duplicates"] = len(df)

    # Market names and taluka
    df["market"] = df["market"].apply(normalize_market)
    df["taluka"] = df["market"].map(MARKET_TALUKA)
    unmapped = sorted(df.loc[df["taluka"].isna(), "market"].unique())

    # One row per day, market and crop (mean across varieties/repeats)
    daily = (
        df.groupby(["date", "district", "taluka", "market", "commodity"], dropna=False)
        .agg(
            min_price=("min_price", "mean"),
            max_price=("max_price", "mean"),
            modal_price=("modal_price", "mean"),
            n_records=("modal_price", "size"),
        )
        .reset_index()
    )
    report["daily market-crop rows"] = len(daily)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(OUT_FILE, index=False)

    print("--- Cleaning report ---")
    for k, v in report.items():
        print(f"{k}: {v}")
    print("date range:", daily["date"].min().date(), "to", daily["date"].max().date())
    print("markets:", daily["market"].nunique(), "| crops:", daily["commodity"].nunique())
    print("unmapped markets (no taluka):", unmapped or "none")
    print("\nRows per crop:")
    print(daily["commodity"].value_counts().to_string())
    print("\nMarkets per taluka:")
    print(daily.groupby("taluka")["market"].nunique().to_string())


if __name__ == "__main__":
    main()