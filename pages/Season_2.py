import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Season 2 Dashboard", layout="wide")

st.title("🀄 Season 2: Live Standings & Stats")

conn = sqlite3.connect("mahjong_league.db")

# 1. Season 2 Leaderboard Query (Single Winners only)
leaderboard_query = """
    SELECT Winner AS Player, 
           COUNT(*) AS Single_Wins, 
           SUM(Points) AS Total_Points
    FROM season_2_hands
    WHERE Action IN ('Ron', 'Tsumo') 
      AND Winner IS NOT NULL 
      AND Winner NOT LIKE '%,%'
    GROUP BY Winner
    ORDER BY Total_Points DESC;
"""

try:
    s2_df = pd.read_sql_query(leaderboard_query, conn)

    # Metric Cards Overview
    col1, col2, col3 = st.columns(3)
    col1.metric("Season 2 Total Hands", pd.read_sql_query("SELECT COUNT(*) FROM season_2_hands", conn).iloc[0,0])
    col2.metric("Current Leader", s2_df.iloc[0]['Player'] if not s2_df.empty else "N/A")
    col3.metric("Top Score", s2_df.iloc[0]['Total_Points'] if not s2_df.empty else 0)

    st.divider()

    # Standings & Visuals
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("🏆 Season 2 Standings")
        st.dataframe(s2_df, use_container_width=True)

    with right_col:
        st.subheader("📊 Points Breakdown")
        if not s2_df.empty:
            fig = px.bar(s2_df, x="Player", y="Total_Points", color="Player", title="Points Scored")
            st.plotly_chart(fig, use_container_width=True)

except Exception:
    st.info("Season 2 games haven't been logged yet or database is syncing!")

conn.close()