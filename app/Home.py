import plotly.express as px
import streamlit as st
from utils import DISCLAIMER, header, kpi_cards, show, sidebar_filters

st.set_page_config(page_title="MandiMap", page_icon="🌾", layout="wide")
header("🌾 MandiMap: Pune Mandi Price Dashboard",
       "Daily wholesale prices (Rs per quintal, as reported) across Pune district markets")

crop, full, d, (start, end) = sidebar_filters()
mk = d.groupby("market")["modal_price"].mean().sort_values()
kpi_cards([
    ("Markets", d["market"].nunique(), f"{d['taluka'].nunique()} talukas"),
    ("Crop", crop, f"{start:%d %b %y} to {end:%d %b %y}"),
    ("Avg modal price", f"Rs {d['modal_price'].mean():,.0f}", "per quintal"),
    ("Highest market avg", f"Rs {mk.max():,.0f}", mk.idxmax()),
    ("Lowest market avg", f"Rs {mk.min():,.0f}", mk.idxmin()),
])

a, b = st.columns([3, 2])
with a:
    daily = d.groupby("date")["modal_price"].mean().reset_index()
    show(px.line(daily, x="date", y="modal_price", title="Average modal price per day (all markets)",
                 labels={"modal_price": "Rs/quintal"}))
with b:
    cov = d.groupby("taluka")["market"].nunique().reset_index(name="markets")
    show(px.pie(cov, names="taluka", values="markets", hole=0.55, title="Markets by taluka"))

mdf = mk.reset_index(name="avg")
show(px.bar(mdf, x="avg", y="market", orientation="h", title="Average modal price by market",
            labels={"avg": "Rs/quintal"}), height=max(300, 28 * len(mdf)))
st.caption(DISCLAIMER)