import pandas as pd
import plotly.express as px
import streamlit as st
from utils import (DISCLAIMER, cluster_today, header, kpi_cards, latest_snapshot,
                   load_clean_live, refresh_live, show)

header("Latest Prices", "Which markets are unusually high or low compared with their own recent prices?")
if st.sidebar.button("Refresh latest prices"):
    refresh_live()
df, live_err = load_clean_live()
if live_err:
    st.warning(f"Could not fetch live prices ({live_err}). Showing the last saved data instead.")
# crops with the most markets reporting in the last 7 days come first, so the page opens on a useful one
recent = df[df["date"] >= df["date"].max() - pd.Timedelta(days=7)]
n_recent = recent.groupby("commodity")["market"].nunique().sort_index().sort_values(ascending=False, kind="stable")
crops = list(n_recent.index) + sorted(set(df["commodity"]) - set(n_recent.index))
crop = st.sidebar.selectbox("Crop", crops,
                            format_func=lambda c: f"{c} ({n_recent.get(c, 0)} markets, last 7 days)")
window = st.sidebar.slider("Comparison window (days)", 14, 60, 30)
full = df[df["commodity"] == crop]

last, t = latest_snapshot(full, window=window)
if t.empty:
    st.warning("No records on the latest date.")
    st.stop()
newest = full["date"].max()
if last < newest:
    n_new = full.loc[full["date"] == newest, "market"].nunique()
    st.info(f"Only {n_new} market(s) reported on {newest:%d %b %Y} so far, so this shows {last:%d %b %Y}, "
            "the latest day with at least 5 markets reporting.")
u, info = cluster_today(t)
# ... everything from here down (out = t.copy(), KPI cards, charts, table) is unchanged
out = t.copy()
out["group"] = "not enough history"
if u is not None:
    out = out.drop(columns="group").merge(u[["market", "group"]], on="market", how="left")
    out["group"] = out["group"].fillna("not enough history")

kpi_cards([("Latest date", f"{last:%d %b %Y}", crop),
           ("Markets reporting", len(t), f"of {full['market'].nunique()}"),
           ("Above own average", int((out["z_score"] > 1).sum()), "z > 1"),
           ("Below own average", int((out["z_score"] < -1).sum()), "z < -1")])
st.caption("Each market is compared with its own previous days; markets that did not report are not filled in. "
           "Recent records are fetched live from data.gov.in and cached for an hour.")
if u is None:
    st.warning("Fewer than 5 markets have enough history for clustering; showing the table only.")
else:
    st.write(f"Grouped on modal price, relative spread and z-score: K = {info['k']}, "
             f"silhouette = {info['silhouette']:.2f}. Exploratory, and separate from the Cluster Analysis page.")

COLORS = {"unusually high today": "#D98E04", "near its usual level": "#8FD19E",
          "unusually low today": "#1B5E3F", "not enough history": "#B8C4BB"}
a, b = st.columns([3, 2])
with a:
    s = out.dropna(subset=["z_score"]).sort_values("z_score")
    show(px.bar(s, x="z_score", y="market", color="group", orientation="h", color_discrete_map=COLORS,
                title="Deviation from own average (z-score)"), height=max(300, 30 * len(s)))
with b:
    with st.container(border=True):
        st.subheader("Highlights")
        flagged = out[out["z_score"].abs() > 2]
        if flagged.empty:
            st.write("No market is more than 2 standard deviations from its own average.")
        for _, r in flagged.iterrows():
            side = "above" if r["z_score"] > 0 else "below"
            st.markdown(f"**{r['market']}**: {abs(r['pct_vs_avg']):.0f}% {side} its {window}-day average (z = {r['z_score']:.1f})")
        st.caption("z = (today's modal price - own average) / own standard deviation. Short windows are noisy.")
cols = ["market", "taluka", "modal_price", "hist_mean", "pct_vs_avg", "z_score", "rel_spread", "hist_n", "group"]
st.dataframe(out[cols].sort_values("z_score", ascending=False).round(2), hide_index=True)
st.caption(DISCLAIMER)