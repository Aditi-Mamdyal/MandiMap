# MandiMap

A Streamlit dashboard for exploring **wholesale vegetable prices in Pune district's mandis (APMC markets)**. It cleans government mandi price data and turns it into market comparisons, price trends, taluka-level analysis, K-Means groups of similar markets, and a live "which markets look unusual today" view.

MandiMap is **descriptive, not predictive**. It shows what prices were and which markets behave alike. It does not forecast prices or recommend where to sell.

## Features

| Page | What it does |
|---|---|
| **Home** | Summary cards (markets, average modal price, highest and lowest market), daily average price line, markets per taluka, average price by market |
| **Market Insights** | Compares markets on price level and price variation, writes plain-language insights, and lets you compare chosen markets side by side |
| **Price Trends** | Price over time for chosen markets (modal, min, max) with an optional 7-day rolling average. Missing days are left as gaps, never filled in |
| **Regional Analysis** | Compares talukas. Each market is averaged first, then markets are averaged within a taluka, so each market counts once |
| **Cluster Analysis** | Groups markets with similar price behaviour using K-Means, with elbow and silhouette charts and a K slider |
| **Latest Prices** | Fetches current prices live from data.gov.in and flags markets that are unusually high or low compared with their own recent prices |

Sidebar controls include crop, a From/To period, the minimum days of data per market, and the number of clusters (K).

## How it works

```
 CSV download (history)  ──►  clean.py  ──►  data/processed/clean.csv ──┐
                                                                        ├──►  Streamlit app
 data.gov.in API (live)  ──►  live.py   ──►  data/processed/live_history.csv ┘
```

1. **Cleaning (`src/clean.py`)**: parses dates, keeps Maharashtra rows, converts prices to numbers, drops missing, zero or impossible rows (min above max, modal outside the min to max range) and exact duplicates, standardises market names (for example `Junnar(Alephata) APMC` becomes `Alephata`), maps each market to its taluka, and aggregates to one row per day, market and crop.
2. **Profiles (`src/features.py`)**: summarises each market-crop pair into average modal price, price volatility (standard deviation), average spread (max minus min) and average relative spread (spread divided by modal price). A profile is *eligible* only with at least 30 days of data by default.
3. **Clustering (`src/clustering.py`)**: standardises the four features, then runs K-Means separately for each crop. K is suggested by the best silhouette score among options that leave no single-market cluster, with the elbow chart as supporting evidence. Cluster labels (relatively lower, intermediate, relatively higher) come from each cluster's mean compared with all markets of that crop.
4. **Latest prices (`src/live.py`)**: fetches Pune's current prices from the API, cleans them with the same logic, and saves each fetch to `live_history.csv` so history keeps growing. If the API is unreachable, the page shows the last saved data with a warning.

### The Latest Prices analysis

For every market, today's modal price is compared with that market's own previous days (30 by default) using a z-score:

```
z = (today's modal price - market's own average) / market's own standard deviation
```

Markets with at least 10 days of history are then grouped with K-Means (K from 2 to 4) on modal price, relative spread and z-score, and named from each group's average z-score: **unusually high today** (above +1), **near its usual level**, or **unusually low today** (below -1). At least 5 markets must qualify, otherwise only the table is shown. The page uses the latest day with at least 5 markets reporting, because a day fills in gradually as markets report.

## Glossary

| Term | Meaning |
|---|---|
| Mandi / APMC | Regulated wholesale market, run by an Agricultural Produce Market Committee |
| Quintal | 100 kg. All prices are in Rs per quintal |
| Modal price | The price at which most trades happened that day |
| Spread | Max price minus min price |
| Relative spread | Spread divided by modal price |
| Volatility | Standard deviation of the modal price |
| Variation (std/mean) | Volatility relative to the price level (coefficient of variation) |
| Z-score | How many standard deviations a value is from an average |
| Silhouette | Cluster quality score from -1 to 1 (the app treats below 0.25 as weak) |
| Taluka | Sub-district administrative unit |

## Project structure

```
MandiMap/
├── app/
│   ├── Home.py                    # entry point
│   ├── utils.py                   # shared filters, styling, snapshot and clustering helpers
│   └── pages/
│       ├── 1_market_insights.py
│       ├── 2_price_trends.py
│       ├── 3_regional_analysis.py
│       ├── 4_cluster_analysis.py
│       └── 5_latest_prices.py
├── src/
│   ├── config.py                  # market name aliases and market-to-taluka mapping
│   ├── clean.py                   # raw data cleaning
│   ├── features.py                # market-crop profiles
│   ├── clustering.py              # K-Means, K selection, cluster descriptions
│   ├── live.py                    # data.gov.in API client and live history
│   └── probe_api.py               # small script for exploring the API
├── data/
│   └── raw/mandimapcsv.csv        # downloaded history
├── .streamlit/config.toml         # theme
└── requirements.txt
```

`data/processed/` is created by the scripts and is git-ignored.

## Getting started

**Requirements:** Python 3.10 or newer.

```bash
git clone https://github.com/Aditi-Mamdyal/MandiMap.git
cd MandiMap

python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

**1. Get an API key.** Register on [data.gov.in](https://www.data.gov.in), generate an API key, and create a `.env` file in the project root:

```
DATA_GOV_API_KEY=your_key_here
```

`.env` is git-ignored. Never commit your key or paste URLs that contain it.

**2. Build the cleaned dataset** from the bundled CSV:

```bash
python src/clean.py
```

**3. (Optional) Fetch live prices once** to check your key and start saving history:

```bash
python src/live.py
```

**4. Run the app:**

```bash
streamlit run app/Home.py
```

Optional command-line reports: `python src/features.py` (profile summary) and `python src/clustering.py` (clustering report for every crop).

### Keeping history up to date

The live API only exposes the latest reporting day, so history grows only on days when `python src/live.py` runs or the Latest Prices page is opened. To avoid gaps, schedule `python src/live.py` once a day, late in the day so most markets have reported (Windows Task Scheduler or cron). Re-download the CSV and rerun `python src/clean.py` from time to time to refresh the long history. Where a day appears in both sources, the live version is used.

## Data sources

Both datasets come from the [Open Government Data (OGD) Platform India](https://www.data.gov.in):

- **Historical prices:** daily variety-wise market prices of commodities (downloaded as CSV).
- **Live prices:** *Current Daily Price of Various Commodities from Various Markets (Mandi)*, fetched through the API.

The underlying prices are reported by APMC markets. Check the dataset pages for licence and terms of use.

## Limitations

- There are only about 9 to 13 markets per crop, so clusters are **exploratory**.
- Results describe reported prices. A cluster with higher prices is not necessarily a better place to sell, because transport, fees, quality, quantity and timing all affect the real return.
- Missing days are not estimated. Reporting varies by market and day.
- Live history has gaps for days when no fetch happened.
- Price level and volatility tend to rise together, partly because a standard deviation in rupees grows with the price. The relative spread and variation measures are included for this reason.

## Tech stack

Python, pandas, NumPy, scikit-learn (K-Means, silhouette), Plotly, Streamlit, Requests, python-dotenv.
