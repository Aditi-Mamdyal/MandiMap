import plotly.express as px
import streamlit as st
from utils import DISCLAIMER, header, show, profiles_for, sidebar_filters

header("Regional Analysis", "Pune talukas compared")
st.caption(DISCLAIMER)
crop, full, d, (start, end) = sidebar_filters()
min_days = st.sidebar.slider("Minimum days of data per market", 10, 90, 30)

p = profiles_for(d, start, end, min_days)
p = p[p["eligible"]].copy()
if p.empty:
    st.warning("No markets have enough data.")
    st.stop()
p["variation"] = p["price_volatility"] / p["avg_modal_price"]

talukas = sorted(p["taluka"].unique())
chosen = st.sidebar.multiselect("Talukas", talukas, default=talukas)
p = p[p["taluka"].isin(chosen)]

# Aggregation rule: first one average per market, then average the markets within a taluka
g = p.groupby("taluka").agg(markets=("market", "nunique"), avg_price=("avg_modal_price", "mean"),
                            avg_variation=("variation", "mean")).reset_index()
st.caption("Taluka figures = mean of the market-level averages (each market counts once), "
           "not a mean of every daily row.")
a, b = st.columns(2)
a.plotly_chart(px.bar(g, x="taluka", y="markets", title="Markets per taluka"))
b.plotly_chart(px.bar(g, x="taluka", y="avg_price", title="Average modal price by taluka"))
show(px.bar(g, x="taluka", y="avg_variation", title="Price variation by taluka (std/mean)"))
show(px.bar(p.sort_values("avg_modal_price"), x="market", y="avg_modal_price", color="taluka",
                       title="Market-level average modal price"))
single = g[g["markets"] == 1]["taluka"].tolist()
if single:
    st.info("Single-market talukas (" + ", ".join(single) + "): the figure is that one market, not a taluka average.")
st.dataframe(p[["market", "taluka", "avg_modal_price", "price_volatility", "variation", "n_obs"]]
             .round(2), hide_index=True)