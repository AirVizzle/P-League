

import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="Mahjong League Stats", layout="wide")

# 2. Google Sheets Published CSV Link
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=170190578&single=true&output=csv"



# 3. Load & Sync Data into SQLite
@st.cache_data(ttl=60)  # Refresh cache every 60 seconds
def load_and_sync_data():
    # Read live CSV from Google Sheets
    df = pd.read_csv(CSV_URL)

    # Connect to local SQLite database (creates 'mahjong_league.db' in project folder)
    conn = sqlite3.connect("mahjong_league.db")

    # Push dataframe into SQLite table 'season_1_hands'
    df.to_sql("season_1_hands", conn, if_exists="replace", index=False)
    conn.close()

    return df


# Fetch data
try:
    df = load_and_sync_data()
    st.title("🀄  Mahjong League Dashboard")

    # Top Metrics / Quick Stats
    st.subheader("Recent Hands")
    st.dataframe(df.head(10), use_container_width=True)

    # Example Interactive Plotly Graph: Action Distribution (Ron vs Tsumo vs Ryuukyoku)
    if "Action" in df.columns:
        st.subheader("Hand Outcomes Overview")
        action_counts = df["Action"].value_counts().reset_index()
        action_counts.columns = ["Action", "Count"]

        fig = px.bar(
            action_counts,
            x="Action",
            y="Count",
            color="Action",
            title="Total Actions Played",
        )
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(
        f"Could not load data. Make sure CSV_URL is correct and published: {e}"
    )