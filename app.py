# app.py
import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.express as px
from datetime import date
import os

st.set_page_config(page_title="Federal Funds Rate", layout="wide")
st.title("Federal Funds Rate (FEDFUNDS) — Historical")

# FRED API key (set in Streamlit Cloud secrets)
fred_key = st.secrets["FRED"]["Key"]
fred = Fred(api_key=fred_key)

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
fig = px.line(df, x="date", y="Federal Funds Rate", title="Federal Funds Rate (Effective)", markers=True)
fig.update_layout(yaxis_title="Percent (%)", xaxis_title="Date", hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# Show latest data and CSV download
st.subheader("Data (latest rows)")
st.write(df.tail())
csv = df.to_csv(index=False)
st.download_button("Download CSV", csv, file_name="fedfunds.csv", mime="text/csv")
