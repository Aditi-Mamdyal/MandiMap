import pandas as pd
import plotly.express as px
import streamlit as st
from utils import DISCLAIMER, header, show, level, profiles_for, sidebar_filters

header("Market Insights", "Compare price levels and stability across markets")
st.caption(DISCLAIMER)
crop, full, d, (start, end) = sidebar_filters()
min_days = st.sidebar.slider("Minimum days of data per market", 10, 90, 30)

p = profiles_for(d, start, end, min_days)
p = p[p["eligible"]].copy()
if len(p) < 3:
    st.warning("Not enough markets with sufficient data for a comparison.")
    st.stop()

p["variation"] = p["price_volatility"] / p["avg_modal_price"]  # coefficient of variation
zp = (p["avg_modal_price"] - p["avg_modal_price"].mean()) / p["avg_modal_price"].std(ddof=0)
zv = (p["variation"] - p["variation"].mean()) / p["variation"].std(ddof=0)
p["price_category"] = zp.map(lambda z: level(z, "Relatively lower", "Intermediate", "Relatively higher"))
p["price_variation"] = zv.map(lambda z: level(z, "Low", "Medium", "High"))

st.subheader("A. Market price comparison")
tbl = p[["market", "taluka", "avg_modal_price", "variation", "price_variation",
          "price_category", "n_obs"]].sort_values("avg_modal_price")
tbl.columns = ["Market", "Taluka", "Avg modal price", "Variation (std/mean)", "Price variation",
                "Relative price category", "Days of data"]
st.dataframe(tbl.round(2), hide_index=True)
st.caption("Categories compare markets against the other markets in this selection only.")

st.subheader("B. Plain-language insights")
for _, r in p.iterrows():
    if r["price_category"] != "Intermediate":
        st.write(f"- **{r['market']}** had a {r['price_category'].lower()} average modal price than "
                 f"other markets in this selection ({r['n_obs']} days of data).")
    if r["price_variation"] == "High":
        st.write(f"- Prices in **{r['market']}** fluctuated more than in many other markets.")
    elif r["price_variation"] == "Low":
        st.write(f"- Prices in **{r['market']}** were relatively stable.")

st.subheader("C. Compare markets")
pick = st.multiselect("Select two or more markets", sorted(p["market"]),
                      default=list(p.sort_values("n_obs", ascending=False)["market"][:2]))
if len(pick) >= 2:
    sel = d[d["market"].isin(pick)]
    show(px.line(sel, x="date", y="modal_price", color="market",
                            labels={"modal_price": "Modal price (Rs/quintal)"}))
    st.dataframe(tbl[tbl["Market"].isin(pick)].round(2), hide_index=True)
else:
    st.info("Select at least two markets.")