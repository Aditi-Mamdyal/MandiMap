import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from features import build_profiles  # noqa: E402
import clustering as cl  # noqa: E402
from live import add_history, fetch_recent_pune, merge_live, update_history  # noqa: E402

DISCLAIMER = ("Descriptive analysis of reported historical prices. It is not a forecast, and a "
              "higher average price does not make a market the best place to sell: transport, "
              "fees, quality, quantity and timing all affect the real return.")


GREENS = ["#1B5E3F", "#43A36B", "#8FD19E", "#C9A66B", "#6B4F3A", "#7A8B7F"]
CSS = """<style>
.block-container{padding-top:1.2rem;max-width:1250px}
.banner{background:linear-gradient(90deg,#1B5E3F,#43A36B);color:#fff;border-radius:22px;
 padding:20px 28px;margin-bottom:14px;box-shadow:0 4px 14px rgba(27,94,63,.25)}
.banner h1{color:#fff;margin:0;font-size:1.9rem;padding:0}
.banner p{margin:4px 0 0;opacity:.9;font-size:.95rem}
.kpi{background:#fff;border-radius:18px;padding:14px 16px;text-align:center;
 box-shadow:0 2px 8px rgba(16,51,31,.10);border-bottom:4px solid #43A36B;margin-bottom:10px}
.kpi-l{font-size:.78rem;color:#4F6F5A;text-transform:uppercase;letter-spacing:.04em}
.kpi-v{font-size:1.7rem;font-weight:700;color:#1B5E3F;line-height:1.25}
.kpi-n{font-size:.75rem;color:#7A8B7F}
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-radius:16px;
 border:1px solid #CFE6D3;box-shadow:0 2px 8px rgba(16,51,31,.06)}
</style>"""


def header(title, subtitle=""):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="banner"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def kpi_cards(items):
    """items: list of (label, value, note)."""
    for col, (label, value, note) in zip(st.columns(len(items)), items):
        col.markdown(f'<div class="kpi"><div class="kpi-l">{label}</div>'
                     f'<div class="kpi-v">{value}</div><div class="kpi-n">{note}</div></div>',
                     unsafe_allow_html=True)


def show(fig, height=340):
    fig.update_layout(colorway=GREENS, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#10331F"), margin=dict(l=10, r=10, t=50, b=10),
                      height=height, title_font_size=15, legend_title_text="")
    fig.update_xaxes(gridcolor="#DCEBDD")
    fig.update_yaxes(gridcolor="#DCEBDD")
    with st.container(border=True):
        st.plotly_chart(fig)


@st.cache_data
def load_clean():
    base = pd.read_csv(ROOT / "data" / "processed" / "clean.csv", parse_dates=["date"])
    return add_history(base)          # + every day saved from the API so far


@st.cache_data(ttl=3600, show_spinner="Fetching latest prices from data.gov.in...")
def _live_raw():
    raw = fetch_recent_pune()
    if update_history(raw):           # save to live_history.csv so tomorrow's page still has today
        load_clean.clear()            # make every page re-read clean.csv + saved history
    return raw

def load_clean_live():
    """clean.csv + the latest records from the API. Returns (df, error_message_or_None)."""
    base = load_clean()
    try:
        return merge_live(base, _live_raw()), None
    except Exception as e:                  # no internet, bad key, API down...
        return base, f"{type(e).__name__}: {e}"


def refresh_live():
    _live_raw.clear()


@st.cache_data
def profiles_for(d, start, end, min_obs):
    return build_profiles(d, start, end, min_obs)


def sidebar_filters():
    """Crop + date range. Returns crop, full crop data, period-filtered data, (start, end)."""
    df = load_clean()
    crop = st.sidebar.selectbox("Crop", sorted(df["commodity"].unique()))
    full = df[df["commodity"] == crop]
    lo, hi = full["date"].min().date(), full["date"].max().date()
    st.sidebar.markdown("**Period**")
    c1, c2 = st.sidebar.columns(2)
    start_d = c1.date_input("From", lo, min_value=lo, max_value=hi, format="DD/MM/YYYY")
    end_d = c2.date_input("To", hi, min_value=lo, max_value=hi, format="DD/MM/YYYY")
    if start_d > end_d:
        st.sidebar.error("'From' must be on or before 'To'.")
        st.stop()
    start, end = pd.Timestamp(start_d), pd.Timestamp(end_d)
    d = full[(full["date"] >= start) & (full["date"] <= end)]
    if d.empty:
        st.warning("No data for this selection.")
        st.stop()
    return crop, full, d, (start, end)

def level(z, low, mid, high, cut=0.5):
    if pd.isna(z):
        return "n/a"
    return high if z > cut else low if z < -cut else mid


def latest_snapshot(full, window=30, min_hist=10, min_markets=5):
    """Latest day with at least `min_markets` reporting (else the crop's newest day),
    compared per market with its own previous `window` days."""
    per_day = full.groupby("date")["market"].nunique()
    enough = per_day[per_day >= min_markets]
    last = enough.index.max() if len(enough) else full["date"].max()
    today = full[full["date"] == last]
    hist = full[(full["date"] < last) & (full["date"] >= last - pd.Timedelta(days=window))]
    stats = hist.groupby("market")["modal_price"].agg(hist_mean="mean", hist_std="std", hist_n="count")
    t = today.groupby(["market", "taluka"]).agg(
        modal_price=("modal_price", "mean"), min_price=("min_price", "mean"),
        max_price=("max_price", "mean")).reset_index().join(stats, on="market")
    t["rel_spread"] = (t["max_price"] - t["min_price"]) / t["modal_price"]
    t["z_score"] = (t["modal_price"] - t["hist_mean"]) / t["hist_std"].where(t["hist_std"] > 0)
    t["pct_vs_avg"] = (t["modal_price"] / t["hist_mean"] - 1) * 100
    t["usable"] = (t["hist_n"] >= min_hist) & t["z_score"].notna()
    return last, t


def cluster_today(t):
    """K-Means on today's snapshot: modal price, relative spread, z-score vs own 30-day mean."""
    u = t[t["usable"]].copy().reset_index(drop=True)
    if len(u) < 5:
        return None, None
    X = StandardScaler().fit_transform(u[["modal_price", "rel_spread", "z_score"]])
    best = None
    for k in range(2, min(4, len(u) - 1) + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        sizes = np.bincount(km.labels_)
        s = silhouette_score(X, km.labels_)
        if sizes.min() >= 2 and (best is None or s > best[0]):
            best = (s, k, km.labels_)
    if best is None:
        km = KMeans(n_clusters=2, n_init=10, random_state=42).fit(X)
        best = (silhouette_score(X, km.labels_), 2, km.labels_)
    u["cluster"] = best[2]
    names = {}
    for c, g in u.groupby("cluster"):
        z = g["z_score"].mean()
        names[c] = ("unusually high today" if z > 1 else "unusually low today" if z < -1
                    else "near its usual level")
    u["group"] = u["cluster"].map(names)
    return u, {"k": best[1], "silhouette": best[0]}