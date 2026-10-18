from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
PROFILE_FILE = ROOT / "data" / "processed" / "profiles.csv"
CLUSTER_FILE = ROOT / "data" / "processed" / "clusters.csv"
EVAL_FILE = ROOT / "data" / "processed" / "k_evaluation.csv"

FEATURES = ["avg_modal_price", "price_volatility", "avg_spread", "avg_rel_spread"]
RANDOM_STATE = 42
MAX_K = 5


def evaluate_k(profiles, max_k=MAX_K):
    """Elbow (inertia) and silhouette for each candidate K."""
    X = StandardScaler().fit_transform(profiles[FEATURES])
    rows = []
    for k in range(2, min(max_k, len(profiles) - 1) + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
        rows.append(
            {
                "k": k,
                "inertia": km.inertia_,
                "silhouette": silhouette_score(X, km.labels_),
                "min_cluster_size": int(np.bincount(km.labels_).min()),
            }
        )
    return pd.DataFrame(rows)


def suggest_k(ev):
    """Best silhouette among K values where no cluster is a single market."""
    ok = ev[ev["min_cluster_size"] >= 2]
    if ok.empty:
        ok = ev
    return int(ok.loc[ok["silhouette"].idxmax(), "k"])


def run_kmeans(profiles, k):
    """Fit K-Means; return profiles with cluster labels and centroids in original units."""
    scaler = StandardScaler()
    X = scaler.fit_transform(profiles[FEATURES])
    km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)

    centroids = pd.DataFrame(scaler.inverse_transform(km.cluster_centers_), columns=FEATURES)
    # Renumber clusters so 0 = lowest average price, increasing upward
    order = centroids["avg_modal_price"].rank(method="first").astype(int) - 1
    result = profiles.copy()
    result["cluster"] = pd.Series(km.labels_, index=result.index).map(order.to_dict())
    centroids.index = order
    centroids = centroids.sort_index()
    centroids.index.name = "cluster"
    return result, centroids


def _level(z, low, mid, high, cut=0.5):
    if z > cut:
        return high
    if z < -cut:
        return low
    return mid


def describe_clusters(result):
    """Plain-language labels from cluster means relative to all markets of the crop."""
    overall = result[FEATURES]
    rows = []
    for c, g in result.groupby("cluster"):
        z = (g[FEATURES].mean() - overall.mean()) / overall.std(ddof=0).replace(0, np.nan)
        price = _level(z["avg_modal_price"], "relatively lower", "intermediate", "relatively higher")
        vol = _level(z["price_volatility"], "low", "moderate", "high")
        rows.append(
            {
                "cluster": c,
                "n_markets": len(g),
                "avg_modal_price": g["avg_modal_price"].mean(),
                "price_volatility": g["price_volatility"].mean(),
                "avg_rel_spread": g["avg_rel_spread"].mean(),
                "price_level": price,
                "volatility_level": vol,
                "description": f"{price} prices, {vol} volatility",
                "markets": ", ".join(sorted(g["market"])),
            }
        )
    return pd.DataFrame(rows)


def main():
    profiles = pd.read_csv(PROFILE_FILE)
    eligible = profiles[profiles["eligible"]]

    all_results, all_eval = [], []
    for crop, p in eligible.groupby("commodity"):
        p = p.reset_index(drop=True)
        print("=" * 60)
        print(f"{crop}: {len(p)} eligible market profiles")
        if len(p) < 4:
            print("Too few profiles to cluster; skipped.")
            continue

        corr = p["avg_modal_price"].corr(p["price_volatility"])
        print(f"Correlation of price level and volatility: {corr:.2f}")

        ev = evaluate_k(p)
        ev.insert(0, "commodity", crop)
        all_eval.append(ev)
        print(ev.round(3).to_string(index=False))

        k = suggest_k(ev)
        print(f"Suggested K (best silhouette, no single-market cluster): {k}")

        result, centroids = run_kmeans(p, k)
        result["k_used"] = k
        all_results.append(result)

        summary = describe_clusters(result)
        print(summary.drop(columns="markets").round(2).to_string(index=False))
        for _, r in summary.iterrows():
            print(f"  Cluster {r['cluster']}: {r['markets']}")

    pd.concat(all_results).to_csv(CLUSTER_FILE, index=False)
    pd.concat(all_eval).to_csv(EVAL_FILE, index=False)
    print("\nSaved:", CLUSTER_FILE.name, "and", EVAL_FILE.name)


if __name__ == "__main__":
    main()