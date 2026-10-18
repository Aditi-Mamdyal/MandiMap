from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN_FILE = ROOT / "data" / "processed" / "clean.csv"
PROFILE_FILE = ROOT / "data" / "processed" / "profiles.csv"

MIN_OBS = 30  # minimum distinct days of data for a profile to be clustered


def build_profiles(df, start=None, end=None, min_obs=MIN_OBS):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    if start is not None:
        d = d[d["date"] >= pd.to_datetime(start)]
    if end is not None:
        d = d[d["date"] <= pd.to_datetime(end)]

    d["spread"] = d["max_price"] - d["min_price"]
    d["rel_spread"] = d["spread"] / d["modal_price"].where(d["modal_price"] > 0)

    profiles = (
        d.groupby(["commodity", "market", "taluka"])
        .agg(
            avg_modal_price=("modal_price", "mean"),
            price_volatility=("modal_price", "std"),
            avg_spread=("spread", "mean"),
            avg_rel_spread=("rel_spread", "mean"),
            n_obs=("date", "nunique"),
            first_date=("date", "min"),
            last_date=("date", "max"),
        )
        .reset_index()
    )
    profiles["eligible"] = (profiles["n_obs"] >= min_obs) & profiles[
        ["avg_modal_price", "price_volatility", "avg_spread", "avg_rel_spread"]
    ].notna().all(axis=1)
    return profiles


def main():
    df = pd.read_csv(CLEAN_FILE)
    profiles = build_profiles(df)
    profiles.to_csv(PROFILE_FILE, index=False)

    print("Total market-crop profiles:", len(profiles))
    print("Eligible (>= %d days):" % MIN_OBS, int(profiles["eligible"].sum()))
    print("\nProfiles per crop (eligible / total):")
    summary = profiles.groupby("commodity")["eligible"].agg(["sum", "count"])
    summary.columns = ["eligible", "total"]
    print(summary.to_string())
    print("\nObservation-days per profile (all):")
    print(profiles["n_obs"].describe().round(1).to_string())
    print("\nExcluded profiles:")
    print(
        profiles.loc[~profiles["eligible"], ["commodity", "market", "n_obs"]]
        .sort_values(["commodity", "n_obs"])
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()