import plotly.express as px
import streamlit as st
import clustering as cl
from utils import DISCLAIMER, header, kpi_cards, profiles_for, show, sidebar_filters

header("Cluster Analysis", "K-Means grouping of markets with similar price behaviour")
crop, full, d, (start, end) = sidebar_filters()
min_days = st.sidebar.slider("Minimum days of data per market", 10, 90, 30)

p = profiles_for(d, start, end, min_days)
p = p[p["eligible"]].reset_index(drop=True)
if len(p) < 4:
    st.warning("Too few markets with enough data to cluster.")
    st.stop()

ev = cl.evaluate_k(p)
suggested = cl.suggest_k(ev)
k = st.sidebar.slider("Number of clusters (K)", int(ev["k"].min()), int(ev["k"].max()), suggested)
res, cen = cl.run_kmeans(p, k)
desc = cl.describe_clusters(res)
sil = float(ev.loc[ev["k"] == k, "silhouette"].iloc[0])
kpi_cards([("Crop", crop, f"{start:%d %b %y} to {end:%d %b %y}"), ("Markets clustered", len(p), f"min {min_days} days each"),
           ("Clusters (K)", k, f"suggested: {suggested}"), ("Silhouette", f"{sil:.2f}", "below 0.25 = weak")])
st.caption("Features (standardized): average modal price, price volatility, average spread, relative spread. "
           "With so few markets, treat groups as exploratory.")

res["Cluster"] = "Cluster " + res["cluster"].astype(str)
a, b = st.columns([3, 2])
with a:
    show(px.scatter(res, x="avg_modal_price", y="price_volatility", color="Cluster", text="market", size="n_obs",
                    title="Market groups", labels={"avg_modal_price": "Avg modal price (Rs)", "price_volatility": "Volatility (std)"}),
         height=380)
with b:
    cnt = res["Cluster"].value_counts().reset_index()
    cnt.columns = ["Cluster", "markets"]
    show(px.pie(cnt, names="Cluster", values="markets", hole=0.55, title="Cluster distribution"), height=380)

feat = {"avg_modal_price": "Avg price", "price_volatility": "Volatility", "avg_rel_spread": "Relative spread"}
z = (res.groupby("Cluster")[list(feat)].mean() - res[list(feat)].mean()) / res[list(feat)].std(ddof=0)
z = z.reset_index().melt("Cluster")
z["feature"] = z["variable"].map(feat)
c1, c2 = st.columns([3, 2])
with c1:
    show(px.bar(z, x="Cluster", y="value", color="feature", barmode="group", title="Cluster profiles",
                labels={"value": "vs. all markets (std devs)"}))
with c2:
    with st.container(border=True):
        st.subheader("Insights")
        for _, r in desc.iterrows():
            st.markdown(f"**Cluster {r['cluster']}**: {r['description']}  \n{r['markets']}")
        if (desc["n_markets"] == 1).any():
            st.warning("At least one cluster has a single market.")
        st.caption("Labels are relative to the markets shown here, not absolute.")

e1, e2 = st.columns(2)
with e1:
    show(px.line(ev, x="k", y="inertia", markers=True, title="Elbow method (inertia)"), height=280)
with e2:
    show(px.line(ev, x="k", y="silhouette", markers=True, title="Silhouette score"), height=280)

with st.expander("Centroids and market table"):
    st.dataframe(cen.round(2))
    st.dataframe(res.sort_values(["cluster", "market"])[["cluster", "market", "taluka", "avg_modal_price",
                 "price_volatility", "avg_rel_spread", "n_obs"]].round(2), hide_index=True)
st.caption(DISCLAIMER)