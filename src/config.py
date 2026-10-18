# Cleaned market name (after removing "APMC" and extra spaces) -> canonical name
MARKET_ALIASES = {
    "Indapur": "Indapur",
    "Junnar": "Junnar",
    "Junnar(Alephata)": "Alephata",
    "Junnar(Narayangaon)": "Narayangaon",
    "Junnar(Otur)": "Otur",
    "Khed": "Khed",
    "Khed(Chakan)": "Chakan",
    "Khed(Shel Pimpalgaon)": "Shel Pimpalgaon",
    "Manchar": "Manchar",
    "Pune": "Pune",
    "Pune(Khadiki)": "Khadiki",
    "Pune(Manjri)": "Manjri",
    "Pune(Moshi)": "Moshi",
    "Pune(Pimpri)": "Pimpri",
}

# Canonical market -> taluka
MARKET_TALUKA = {
    "Junnar": "Junnar",
    "Alephata": "Junnar",
    "Narayangaon": "Junnar",
    "Otur": "Junnar",
    "Khed": "Khed",
    "Chakan": "Khed",
    "Shel Pimpalgaon": "Khed",
    "Manchar": "Ambegaon",
    "Indapur": "Indapur",
    "Pune": "Pune City",
    "Khadiki": "Pune City",
    "Manjri": "Haveli",
    "Moshi": "Haveli",
    "Pimpri": "Pimpri Chinchwad",
}

MIN_PRICE_COLS = ["min_price", "max_price", "modal_price"]