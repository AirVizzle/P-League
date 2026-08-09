import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Player Profile", layout="wide")

st.title("👤 Individual Player Statistics")

# Connect to local SQLite database
conn = sqlite3.connect("mahjong_league.db")

# Get list of unique single players for the dropdown menu
players_query = """
    SELECT DISTINCT Winner AS Player 
    FROM season_1_hands 
    WHERE Winner IS NOT NULL AND Winner NOT LIKE '%,%'
    ORDER BY Winner ASC;
"""
players_df = pd.read_sql_query(players_query, conn)
player_list = players_df["Player"].tolist()

# Fallback in case no players are found
if not player_list:
    st.warning("No single-player stats found in the database.")
    st.stop()

# Selectbox to choose a player
selected_player = st.selectbox("Select a Player:", player_list)

st.markdown(f"## Statistics for **{selected_player}**")

# Query 1: Single-Winner Hands Scored (Excludes Ryuukyoku & Multi-Winner split hands)
wins_query = """
    SELECT Action, Points, Hand
    FROM season_1_hands 
    WHERE Winner = ? 
      AND Action IN ('Ron', 'Tsumo')
      AND Winner NOT LIKE '%,%';
"""
wins_df = pd.read_sql_query(wins_query, conn, params=(selected_player,))

# Query 2: Direct Deal-Ins as Payer (Excludes Ryuukyoku payments)
deal_ins_query = """
    SELECT Winner, Points, Hand
    FROM season_1_hands 
    WHERE Action = 'Ron' 
      AND Payer LIKE ?
      AND Winner NOT LIKE '%,%';
"""
deal_ins_df = pd.read_sql_query(
    deal_ins_query, conn, params=(f"%{selected_player}%",)
)

conn.close()

# Top Summary Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Number of Wins", len(wins_df))
col2.metric("Total Points Scored", int(wins_df["Points"].sum()))
col3.metric("Direct Deal-Ins", len(deal_ins_df))

st.divider()

# Detailed Tables Setup
tab1, tab2 = st.tabs(["Winning History", "Deal-In History"])

with tab1:
    st.subheader("Winning Hands (Single Winner Only)")
    if not wins_df.empty:
        st.dataframe(wins_df, use_container_width=True)
    else:
        st.info("No single-winner hands recorded for this player.")

with tab2:
    st.subheader("Direct Deal-Ins")
    if not deal_ins_df.empty:
        st.dataframe(deal_ins_df, use_container_width=True)
    else:
        st.info("No direct deal-ins recorded for this player.")