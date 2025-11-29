# app.py
import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import os
import requests
from functools import reduce

# Create figure
fig = go.Figure()

# FRED API key (set in Streamlit Cloud secrets)
fred_key = st.secrets["FRED"]["Key"]
fred = Fred(api_key=fred_key)

# Pull full FRED metadata (all series in all categories)
def get_all_fred_metadata(api_key):
    base = "https://api.stlouisfed.org/fred"
    headers = {"Authorization": f"Bearer {api_key}"}  # Use header instead of URL query
    all_data = []

    # Start from the root category
    root_id = 0
    categories_to_visit = [root_id]
    visited = set()

    while categories_to_visit:
        cat = categories_to_visit.pop()
        if cat in visited:
            continue
        visited.add(cat)

        # Get series in this category
        series_url = f"{base}/category/series?category_id={cat}&api_key={api_key}&file_type=json"
        r = requests.get(series_url).json()

        if "seriess" in r:
            for s in r["seriess"]:
                all_data.append({
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "units": s.get("units"),
                    "frequency": s.get("frequency"),
                    "seasonal_adjustment": s.get("seasonal_adjustment"),
                    "last_updated": s.get("last_updated"),
                    "notes": s.get("notes")
                })

        # Traverse child categories
        children_url = f"{base}/category/children?category_id={cat}&api_key={api_key}&file_type=json"
        r = requests.get(children_url).json()

        if "categories" in r:
            for c in r["categories"]:
                categories_to_visit.append(c["id"])

    df_meta = pd.DataFrame(all_data)
    return df_meta

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Economic Dashboard", layout="wide")
st.title("Economic Indicators Dashboard")

# --- FRED API key ---
fred_key = st.secrets["FRED"]["Key"]
fred = Fred(api_key=fred_key)

# --- Function to load FRED series ---
@st.cache_data(ttl=3600)
def load_fred_series(series_id, start, end):
    s = fred.get_series(series_id, observation_start=start, observation_end=end)
    df = s.to_frame(name="Value").reset_index()
    df.rename(columns={"index": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    return df

# --- Function to pull full FRED metadata ---
def get_all_fred_metadata(api_key):
    base = "https://api.stlouisfed.org/fred"
    headers = {"Authorization": f"Bearer {api_key}"}
    all_data = []

    root_id = 0
    categories_to_visit = [root_id]
    visited = set()

    while categories_to_visit:
        cat = categories_to_visit.pop()
        if cat in visited:
            continue
        visited.add(cat)

        series_url = f"{base}/category/series?category_id={cat}&file_type=json"
        r = requests.get(series_url, headers=headers).json()
        if "seriess" in r:
            for s in r["seriess"]:
                all_data.append({
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "units": s.get("units"),
                    "frequency": s.get("frequency"),
                    "seasonal_adjustment": s.get("seasonal_adjustment"),
                    "last_updated": s.get("last_updated"),
                    "notes": s.get("notes")
                })

        children_url = f"{base}/category/children?category_id={cat}&file_type=json"
        r = requests.get(children_url, headers=headers).json()
        if "categories" in r:
            for c in r["categories"]:
                categories_to_visit.append(c["id"])

    return pd.DataFrame(all_data)

# --- Date Selection ---
start_default = "2000-01-01"
end_default = date.today().isoformat()
start = st.date_input("Start date", pd.to_datetime(start_default), key = 'start_date')
end = st.date_input("End date", pd.to_datetime(end_default), key = 'end_date')
if start > end:
    st.error("Start date must be before end date.")
    st.stop()

# --- Region Selection ---
region = st.selectbox("Select region:", ["National", "Missouri", "Kansas"], key='region')

# --- Map Variables to Series IDs (state level) ---
series_map = {
    "National": {
        "Federal Funds Rate": "FEDFUNDS",
        "Unemployment Rate": "UNRATE",
        "GDP Growth %": "GDPC1",
        "Inflation %": "CPIAUCNS"
    },
    "Missouri": {
        "Unemployment Rate": "MOUR",
        "State Minimum Wage Rate": "STTMINWGMO",
        "Resident Population in Thousands": "MOPOP",
        "Gross Domestic Product: All Industry Total": "MONQGSP",
        "Real Median Household Income": "MEHOINUSMOA672N",
    "Per Capita Personal Income": "MOPCPI",
    "Median Household Income": "MEHOINUSMOA646N",
    "Labor Force Participation Rate": "LBSSA29",
    "SNAP Benefits Recipients": "BR29000MOA647NCEN",
    "Housing Inventory: Median Listing Price": "MEDLISPRIMO",
    "Homeownership Rate": "MOHOWN"
    },
    "Kansas": {
    "Unemployment Rate": "KSUR",  # Monthly, Seasonally Adjusted
    "State Minimum Wage Rate": "STTMINWGKS",  # Annual, Not Seasonally Adjusted
    "Resident Population in Thousands": "KSPOP",  # Annual, Not Seasonally Adjusted
    "Gross Domestic Product: All Industry Total (Quarterly, SAAR)": "KSNQGSP",
    "Real Median Household Income": "MEHOINUSKSA672N",
    "Per Capita Personal Income": "KSPCPI",
    "Median Household Income": "MEHOINUSKSA646N",
    "Labor Force Participation Rate": "LBSSA20",
    "SNAP Benefits Recipients": "BRKS20M647NCEN",
    "Housing Inventory: Median Listing Price": "MEDLISPRIKS",
    "Homeownership Rate": "KSHOWN"
    }
}


# --- Interactive Series Selection ---
series_options = list(series_map[region].keys())
selected_series = st.multiselect(
    "Select series to display on the chart:",
    options=series_options,
    default=series_options[:2],
    key='series_selector'
)

# --- Checkbox for Z-score Standardization ---
use_zscore = st.checkbox("Normalize using Z-score (standardization)", value=False)

# --- Load Data with error handling ---
# Load series with try/except
df_list = []
failed_series = []
for var in selected_series:
    series_id = series_map[region][var]
    try:
        df_temp = load_fred_series(series_id, start.isoformat(), end.isoformat())
        df_temp.rename(columns={"Value": var}, inplace=True)
        df_list.append(df_temp)
    except ValueError as e:
        failed_series.append(f"{var} ({series_id}): {e}")

# Merge all successfully loaded series
if df_list:
    df = reduce(lambda left, right: pd.merge(left, right, on="date", how="outer"), df_list)
    df = df.sort_values("date")
else:
    st.error("No data available for the selected series and date range.")
    st.stop()

# Apply Z-score if requested
if use_zscore:
    df_to_plot = df.copy()
    for col in df.columns:
        if col != "date":
            df_to_plot[col] = (df_to_plot[col] - df_to_plot[col].mean()) / df_to_plot[col].std()
else:
    df_to_plot = df

# Plot using df_to_plot
fig = go.Figure()
colors = ["blue", "red", "green", "orange", "purple", "brown", "pink", "cyan"]
for i, series in enumerate(selected_series):
    if series in df_to_plot.columns:  # safe check
        fig.add_trace(go.Scatter(
            x=df_to_plot["date"],
            y=df_to_plot[series],
            mode="lines+markers",
            name=series,
            line=dict(color=colors[i % len(colors)])
        ))

fig.update_layout(
    title=f"Economic Indicators ({region})",
    xaxis_title="Date",
    yaxis_title="Value",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# Notify user about failed series
if failed_series:
    st.warning("Some series could not be loaded:")
    for msg in failed_series:
        st.write(msg)

# --- Optional: show data ---
st.subheader("Data (latest rows)")
st.write(df.tail())
csv = df.to_csv(index=False)
st.download_button("Download CSV", csv, file_name="economic_data.csv", mime="text/csv")

st.subheader("FRED Metadata Catalogue")

if st.button("Download FRED Metadata"):
    with st.spinner("Retrieving full FRED metadata (this may take ~20–40 seconds)..."):
        df_meta = get_all_fred_metadata(fred_key)

    st.success(f"Retrieved {len(df_meta):,} series.")

    # Show preview
    st.write(df_meta.head())

    # CSV download
    csv_meta = df_meta.to_csv(index=False)
    st.download_button(
        "Download FRED Metadata CSV",
        csv_meta,
        file_name="fred_metadata_catalogue.csv",
        mime="text/csv"
    )
