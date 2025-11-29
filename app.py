# app.py
import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import os
import requests

# Create figure
fig = go.Figure()

st.set_page_config(page_title="Federal Funds Rate", layout="wide")
st.title("Federal Funds Rate (FEDFUNDS) — Historical")

# FRED API key (set in Streamlit Cloud secrets)
fred_key = st.secrets["FRED"]["Key"]
fred = Fred(api_key=fred_key)

# Pull full FRED metadata (all series in all categories)
def get_all_fred_metadata(api_key):
    base = "https://api.stlouisfed.org/fred"
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



# Date selector
start_default = "2000-01-01"
end_default = date.today().isoformat()
start = st.date_input("Start date", pd.to_datetime(start_default))
end = st.date_input("End date", pd.to_datetime(end_default))

if start > end:
    st.error("Start date must be before end date.")
    st.stop()

# Load data
@st.cache_data(ttl=3600)
def load_fred_series(series_id, start, end):
    s = fred.get_series(series_id, observation_start=start, observation_end=end)
    df = s.to_frame(name="Federal Funds Rate").reset_index()
    df.rename(columns={"index": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_fred_series("FEDFUNDS", start.isoformat(), end.isoformat())

# Plot chart
#fig = px.line(df, x="date", y="Federal Funds Rate", title="Federal Funds Rate (Effective)", markers=True)
#fig.update_layout(yaxis_title="Percent (%)", xaxis_title="Date", hovermode="x unified")
#st.plotly_chart(fig, use_container_width=True)

# Load Federal Funds Rate
df_fed = load_fred_series("FEDFUNDS", start.isoformat(), end.isoformat())

# Load Unemployment Rate
df_unemp = load_fred_series("UNRATE", start.isoformat(), end.isoformat())
df_unemp.rename(columns={"Federal Funds Rate": "Unemployment Rate"}, inplace=True)

# Load additional series
df_gdp = load_fred_series("GDPC1", start.isoformat(), end.isoformat())  # Real GDP (quarterly)
df_gdp.rename(columns={"Federal Funds Rate": "Real GDP"}, inplace=True)

# Compute quarterly GDP growth rate (YoY)
df_gdp["GDP Growth %"] = df_gdp["Real GDP"].pct_change(periods=4) * 100

df_cpi = load_fred_series("CPIAUCNS", start.isoformat(), end.isoformat())  # CPI, all urban consumers
# Year-over-year CPI inflation
df_cpi["Inflation %"] = df_cpi["Federal Funds Rate"].pct_change(periods=12) * 100

# Merge all series
# df = pd.merge(df, df_gdp[["date", "GDP Growth %"]], on="date", how="outer")
# df = pd.merge(df, df_cpi[["date", "Inflation %"]], on="date", how="outer")
# df = df.sort_values("date")

# Merge all series step by step, starting from df_fed
df = df_fed.copy()
df = pd.merge(df, df_unemp, on="date", how="outer")
df = pd.merge(df, df_gdp[["date", "GDP Growth %"]], on="date", how="outer")
df = pd.merge(df, df_cpi[["date", "Inflation %"]], on="date", how="outer")
df = df.sort_values("date")

# --- Interactive selection ---
series_options = ["Federal Funds Rate", "Unemployment Rate", "GDP Growth %", "Inflation %"]
selected_series = st.multiselect(
    "Select series to display on the chart:",
    options=series_options,
    default=["Federal Funds Rate", "Unemployment Rate"]  # default selection
)

# --- Plot selected series ---
fig = go.Figure()
colors = {
    "Federal Funds Rate": "blue",
    "Unemployment Rate": "red",
    "GDP Growth %": "green",
    "Inflation %": "orange"
}

for series in selected_series:
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df[series],
        mode="lines+markers",
        name=series,
        line=dict(color=colors[series])
    ))

fig.update_layout(
    title="Economic Indicators",
    xaxis_title="Date",
    yaxis_title="Percent (%)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# --- Optional: show data ---
st.subheader("Data (latest rows)")
st.write(df.tail())
csv = df.to_csv(index=False)
st.download_button("Download CSV", csv, file_name="economic_data.csv", mime="text/csv")

# Merge on date
# df = pd.merge(df_fed, df_unemp, on="date", how="outer").sort_values("date")

# Add Federal Funds Rate line
# fig.add_trace(go.Scatter(
#     x=df["date"],
#     y=df["Federal Funds Rate"],
#     mode="lines+markers",
#     name="Federal Funds Rate",
#     line=dict(color="blue")
# ))

# Add Unemployment Rate line
# fig.add_trace(go.Scatter(
#     x=df["date"],
#     y=df["Unemployment Rate"],
#     mode="lines+markers",
#     name="Unemployment Rate",
#     line=dict(color="red")
# ))

# Add traces to Plotly figure
# fig.add_trace(go.Scatter(
#     x=df["date"],
#     y=df["GDP Growth %"],
#     mode="lines+markers",
#     name="GDP Growth %",
#     line=dict(color="green")
# ))

# fig.add_trace(go.Scatter(
#     x=df["date"],
#     y=df["Inflation %"],
#     mode="lines+markers",
#     name="Inflation %",
#     line=dict(color="orange")
# ))

# Update layout title to reflect new series
# fig.update_layout(
#     title="Federal Funds Rate, Unemployment Rate, GDP Growth, and Inflation",
#     xaxis_title="Date",
#     yaxis_title="Percent (%)",
#     hovermode="x unified"
# )

# # Display in Streamlit
# st.plotly_chart(fig, use_container_width=True)

# # Show latest data and CSV download
# st.subheader("Data (latest rows)")
# st.write(df.tail())
# csv = df.to_csv(index=False)
# st.download_button("Download CSV", csv, file_name="fedfunds.csv", mime="text/csv")

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

