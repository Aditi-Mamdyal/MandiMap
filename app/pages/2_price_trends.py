import pandas as pd
import plotly.express as px
import streamlit as st
from utils import DISCLAIMER, header, show, sidebar_filters

header("Price Trends", "How prices moved over time")
st.caption(DISCLAIMER)
crop, full, d, _ = sidebar_filters()

top = d.groupby("market")["date"].nunique().sort_values(ascending=False)
markets = st.multiselect("Markets", list(top.index), default=list(top.index[:3]))
series = st.multiselect("Prices to show", ["modal_price", "min_price", "max_price"], default=["modal_price"])
smooth = st.checkbox("7-day rolling average", value=False)
if not markets or not series:
    st.info("Choose at least one market and one price series.")
    st.stop()

sel = d[d["market"].isin(markets)].sort_values("date").copy()
if smooth:
    for s in series:
        sel[s] = sel.groupby("market")[s].transform(lambda x: x.rolling(7, min_periods=3).mean())
long = sel.melt(id_vars=["date", "market"], value_vars=series, var_name="series", value_name="price")
fig = px.line(long.dropna(), x="date", y="price", color="market", line_dash="series",
              labels={"price": "Rs/quintal"}, title=f"{crop}: price trends")
show(fig)
st.caption("Missing days are left as gaps, not filled with estimated prices.")