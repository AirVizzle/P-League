import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="All-Time Player Stats", layout="wide")

st.title("👤 All-Time Player Statistics")

# Connect to local SQLite database
conn = sqlite3.connect("mahjong_league.db")


# Helper function to check if a table exists in SQLite
def table_exists(table_name, connection):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone()[0] == 1


# Determine which season tables exist
has_s1 = table_exists("season_1_hands", conn)
has_s2 = table_exists("season_2_hands", conn)

# 1. Fetch Unique Players dynamically based on available tables
player_queries = []
if has_s1:
    player_queries.append(
        "SELECT DISTINCT Winner AS Player FROM season_1_hands WHERE Winner IS NOT NULL AND Winner NOT LIKE '%,%'"
    )
if has_s2:
    player_queries.append(
        "SELECT DISTINCT Winner AS Player FROM season_2_hands WHERE Winner IS NOT NULL AND Winner NOT LIKE '%,%'"
    )

if player_queries:
    combined_player_sql = (
        " UNION ".join(player_queries) + " ORDER BY Player ASC;"
    )
    try:
        players_df = pd.read_sql_query(combined_player_sql, conn)
        player_list = players_df["Player"].tolist()
    except Exception:
        player_list = []
else:
    player_list = []

if not player_list:
    st.warning(
        "No single-player stats found across any season. Make sure tables are synced!"
    )
    conn.close()
    st.stop()

# Dropdown menu to pick a player
selected_player = st.selectbox("Select a Player:", player_list)

st.markdown(f"## All-Time Statistics for **{selected_player}**")

# 2. Build Wins Query dynamically (Fixed the trailing comma bug!)
win_queries = []
if has_s1:
    win_queries.append("""
        SELECT 'Season 1' AS Season, Action, Points, Hand
        FROM season_1_hands 
        WHERE Winner = ? 
          AND Action IN ('Ron', 'Tsumo')
          AND Winner NOT LIKE '%,%'
    """)
if has_s2:
    win_queries.append("""
        SELECT 'Season 2' AS Season, Action, Points, Hand
        FROM season_2_hands 
        WHERE Winner = ? 
          AND Action IN ('Ron', 'Tsumo')
          AND Winner NOT LIKE '%,%'
    """)

all_time_wins_query = " UNION ALL ".join(win_queries)
win_params = [selected_player] * len(win_queries)

wins_df = (
    pd.read_sql_query(all_time_wins_query, conn, params=win_params)
    if win_queries
    else pd.DataFrame()
)

# 3. Build Deal-Ins Query dynamically
deal_queries = []
if has_s1:
    deal_queries.append("""
        SELECT 'Season 1' AS Season, Winner, Points, Hand
        FROM season_1_hands 
        WHERE Action = 'Ron' 
          AND Payer LIKE ?
          AND Winner NOT LIKE '%,%'
    """)
if has_s2:
    deal_queries.append("""
        SELECT 'Season 2' AS Season, Winner, Points, Hand
        FROM season_2_hands 
        WHERE Action = 'Ron' 
          AND Payer LIKE ?
          AND Winner NOT LIKE '%,%'
    """)

all_time_deal_ins_query = " UNION ALL ".join(deal_queries)
deal_params = [f"%{selected_player}%"] * len(deal_queries)

deal_ins_df = (
    pd.read_sql_query(all_time_deal_ins_query, conn, params=deal_params)
    if deal_queries
    else pd.DataFrame()
)

conn.close()

# --- Display All-Time Metrics ---
# --- Display All-Time Metrics ---
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("All-Time Wins", len(wins_df))
col2.metric("All-Time Points Scored", int(wins_df["Points"].sum()))
col3.metric("All-Time Deal-Ins", len(deal_ins_df))

# Highest Value Hand
highest_hand = wins_df["Points"].max() if not wins_df.empty else 0
col4.metric("Highest Value Hand", int(highest_hand))

# Average Winning Hand Value
avg_hand = wins_df["Points"].mean() if not wins_df.empty else 0
col5.metric("Avg Hand Value", f"{avg_hand:,.0f} pts")

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