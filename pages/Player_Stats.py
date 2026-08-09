import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="All-Time Player Stats", layout="wide")

st.title("👤 All-Time Player Statistics")

# Connect to local SQLite database
conn = sqlite3.connect("mahjong_league.db")

# 1. SQL Query to combine all players across both seasons
all_players_query = """
    SELECT DISTINCT Winner AS Player FROM season_1_hands WHERE Winner IS NOT NULL AND Winner NOT LIKE '%,%'
    UNION
    SELECT DISTINCT Winner AS Player FROM season_2_hands WHERE Winner IS NOT NULL AND Winner NOT LIKE '%,%'
    ORDER BY Player ASC;
"""

try:
    players_df = pd.read_sql_query(all_players_query, conn)
    player_list = players_df["Player"].tolist()
except Exception:
    player_list = []

if not player_list:
    st.warning("No single-player stats found across any season.")
    st.stop()

# Dropdown menu to pick a player
selected_player = st.selectbox("Select a Player:", player_list)

st.markdown(f"## All-Time Statistics for **{selected_player}**")

# 2. SQL Query: Combine all single-winning hands across both seasons
all_time_wins_query = """
    SELECT 'Season 1' AS Season, Action, Points, Hand
    FROM season_1_hands 
    WHERE Winner = ? 
      AND Action IN ('Ron', 'Tsumo')
      AND Winner NOT LIKE '%,%'

    UNION ALL

    SELECT 'Season 2' AS Season, Action, Points, Hand,
    FROM season_2_hands 
    WHERE Winner = ? 
      AND Action IN ('Ron', 'Tsumo')
      AND Winner NOT LIKE '%,%';
"""

wins_df = pd.read_sql_query(
    all_time_wins_query, conn, params=(selected_player, selected_player)
)

# 3. SQL Query: Combine all direct deal-ins across both seasons
all_time_deal_ins_query = """
    SELECT 'Season 1' AS Season, Winner, Points, Hand
    FROM season_1_hands 
    WHERE Action = 'Ron' 
      AND Payer LIKE ?
      AND Winner NOT LIKE '%,%'

    UNION ALL

    SELECT 'Season 2' AS Season, Winner, Points, Hand
    FROM season_2_hands 
    WHERE Action = 'Ron' 
      AND Payer LIKE ?
      AND Winner NOT LIKE '%,%';
"""

deal_ins_df = pd.read_sql_query(
    all_time_deal_ins_query,
    conn,
    params=(f"%{selected_player}%", f"%{selected_player}%"),
)

conn.close()

# --- Display All-Time Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("All-Time Wins", len(wins_df))
col2.metric("All-Time Points Scored", int(wins_df["Points"].sum()))
col3.metric("All-Time Deal-Ins", len(deal_ins_df))

# Calculates highest scoring single hand across both seasons
highest_hand = (
    wins_df["Points"].max() if not wins_df.empty else 0
)
col4.metric("Highest Value Hand", int(highest_hand))

st.divider()

# --- Breakdown Tables & Charts ---
tab1, tab2, tab3 = st.tabs(
    ["Winning Hands History", "Deal-In History", "Season Comparison"]
)

with tab1:
    st.subheader("All-Time Winning Hands")
    if not wins_df.empty:
        st.dataframe(wins_df, use_container_width=True)
    else:
        st.info("No single-winner hands recorded for this player.")

with tab2:
    st.subheader("All-Time Direct Deal-Ins")
    if not deal_ins_df.empty:
        st.dataframe(deal_ins_df, use_container_width=True)
    else:
        st.info("No direct deal-ins recorded for this player.")

with tab3:
    st.subheader("Wins Breakdown by Season")
    if not wins_df.empty:
        # Group by season to display progress
        season_breakdown = (
            wins_df.groupby("Season")
            .agg(Wins=("Action", "count"), Total_Points=("Points", "sum"))
            .reset_index()
        )

        fig = px.bar(
            season_breakdown,
            x="Season",
            y="Total_Points",
            color="Season",
            title=f"{selected_player}'s Points Scored per Season",
            text="Total_Points",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No season breakdown available.")