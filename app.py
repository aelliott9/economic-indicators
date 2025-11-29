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

def get_all_fred_metadata_via_search(api_key, limit=500000):
    base = "https://api.stlouisfed.org/fred/series/search"
    all_rows = []
    offset = 0
    page_size = 1000

    while offset < limit:
        url = (
            f"{base}?api_key={api_key}"
            f"&search_text="   # returns *all* series when empty
            f"&file_type=json"
            f"&limit={page_size}"
            f"&offset={offset}"
        )

        r = requests.get(url).json()

        if "seriess" not in r or len(r["seriess"]) == 0:
            break

        all_rows.extend(r["seriess"])
        offset += page_size

    return pd.DataFrame(all_rows)

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

# Merge on date
df = pd.merge(df_fed, df_unemp, on="date", how="outer").sort_values("date")

# Add Federal Funds Rate line
fig.add_trace(go.Scatter(
    x=df["date"],
    y=df["Federal Funds Rate"],
    mode="lines+markers",
    name="Federal Funds Rate",
    line=dict(color="blue")
))

# Add Unemployment Rate line
fig.add_trace(go.Scatter(
    x=df["date"],
    y=df["Unemployment Rate"],
    mode="lines+markers",
    name="Unemployment Rate",
    line=dict(color="red")
))

# Update layout
fig.update_layout(
    title="Federal Funds Rate and Unemployment Rate",
    xaxis_title="Date",
    yaxis_title="Percent (%)",
    hovermode="x unified"
)

# Display in Streamlit
st.plotly_chart(fig, use_container_width=True)

# Show latest data and CSV download
st.subheader("Data (latest rows)")
st.write(df.tail())
csv = df.to_csv(index=False)
st.download_button("Download CSV", csv, file_name="fedfunds.csv", mime="text/csv")

st.subheader("TEST")

st.subheader("FRED Metadata Catalogue")

if st.button("Download FRED Metadata"):
    with st.spinner("Retrieving full FRED metadata (this may take ~20–40 seconds)..."):
        df_meta = get_all_fred_metadata_via_search(fred_key)

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

