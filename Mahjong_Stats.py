import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="Mahjong League Stats", layout="wide")

# 2. Google Sheets Published CSV Links
SEASON_1_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=170190578&single=true&output=csv"
SEASON_2_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=983730091&single=true&output=csv"
GAME_LOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=721192921&single=true&output=csv"


# 3. Load & Sync Data into SQLite
@st.cache_data(ttl=60)  # Refresh cache every 60 seconds
def load_and_sync_data():
    conn = sqlite3.connect("mahjong_league.db")

    # --- Sync Season 1 ---
    try:
        df_s1 = pd.read_csv(SEASON_1_URL)
        df_s1.to_sql("season_1_hands", conn, if_exists="replace", index=False)
    except Exception as e:
        st.warning(f"Could not load Season 1 data: {e}")

    # --- Sync Season 2 ---
    try:
        df_s2 = pd.read_csv(SEASON_2_URL)
        df_s2.to_sql("season_2_hands", conn, if_exists="replace", index=False)
    except Exception as e:
        st.warning(f"Could not load Season 2 data: {e}")

    # --- Sync Game Log / Schedule ---
    try:
        df_game_log = pd.read_csv(GAME_LOG_URL)
        df_game_log.to_sql("game_log", conn, if_exists="replace", index=False)
    except Exception as e:
        st.warning(f"Could not load Game Log data: {e}")

    conn.close()
    return True


# 4. Helper Function: Generate Dynamic Weekly Ticker
@st.cache_data(ttl=60)
def get_week_ticker_text(target_week="Week 1"):
    try:
        df = pd.read_csv(GAME_LOG_URL)
        ticker_items = []

        # Filter for the target week if 'Week' column exists
        week_games = (
            df[df["Week"] == target_week] if "Week" in df.columns else df
        )

        for _, row in week_games.iterrows():
            group = row.get("Group", "Match") if "Group" in df.columns else "Match"

            # Check if game has scores logged
            if (
                pd.notna(row.get("Score 1"))
                and str(row.get("Score 1")).strip() != ""
            ):
                p1, s1 = row.get("Player 1", ""), row.get("Score 1", 0)
                p2, s2 = row.get("Player 2", ""), row.get("Score 2", 0)
                p3, s3 = row.get("Player 3", ""), row.get("Score 3", 0)
                p4, s4 = row.get("Player 4", ""), row.get("Score 4", 0)

                match_str = f"🏆 [{target_week} - {group} Result]: {p1} ({s1}) | {p2} ({s2}) | {p3} ({s3}) | {p4} ({s4})"
            else:
                players = [
                    str(row.get(f"Player {i}"))
                    for i in range(1, 5)
                    if pd.notna(row.get(f"Player {i}"))
                ]
                player_list_str = (
                    ", ".join(players) if players else "Players TBD"
                )
                match_str = f"⏳ [{target_week} - {group}]: {player_list_str} ➔ Status: TBA"

            ticker_items.append(match_str)

        if not ticker_items:
            return f"🀄 {target_week} Schedule: No matches posted yet."

        return " &nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp; ".join(
            ticker_items
        )

    except Exception:
        return "🀄 Welcome to P League! Check match details in the schedule tab."


# --- App Execution ---
try:
    # Trigger database sync
    load_and_sync_data()

    # 5. Display Rolling Match Ticker
    ticker_text = get_week_ticker_text(target_week="Week 1")
    ticker_html = f"""
    <style>
    .ticker-wrap {{
        width: 100%;
        background-color: #11111b;
        color: #cba6f7;
        padding: 12px 0;
        font-size: 15px;
        font-weight: 600;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        border-left: 4px solid #89b4fa;
        border-radius: 6px;
        margin-bottom: 25px;
        overflow: hidden;
        white-space: nowrap;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    .ticker-move {{
        display: inline-block;
        padding-left: 100%;
        animation: ticker 30s linear infinite;
    }}
    .ticker-move:hover {{
        animation-play-state: paused;
    }}
    @keyframes ticker {{
        0%   {{ transform: translate3d(0, 0, 0); }}
        100% {{ transform: translate3d(-100%, 0, 0); }}
    }}
    </style>
    <div class="ticker-wrap">
        <div class="ticker-move">{ticker_text}</div>
    </div>
    """
    st.markdown(ticker_html, unsafe_allow_html=True)

    # Title
    st.title("🀄 Mahjong League Dashboard")

    # Connect to SQLite to read tables for UI display
    conn = sqlite3.connect("mahjong_league.db")
    df_s2 = pd.read_sql_query("SELECT * FROM season_2_hands", conn)
    df_log = pd.read_sql_query("SELECT * FROM game_log", conn)
    conn.close()

    # 6. Main Dashboard Tabs
    tab_overview, tab_schedule = st.tabs(["📊 Season 2 Hands", "📅 Match Log"])

    with tab_overview:
        st.subheader("Recent Season 2 Hands")
        st.dataframe(df_s2.head(10), use_container_width=True)

        if "Action" in df_s2.columns:
            st.subheader("Hand Outcomes Overview")
            action_counts = df_s2["Action"].value_counts().reset_index()
            action_counts.columns = ["Action", "Count"]

            fig = px.bar(
                action_counts,
                x="Action",
                y="Count",
                color="Action",
                title="Total Actions Played (Season 2)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab_schedule:
        st.subheader("Match Log & Upcoming Tables")
        st.dataframe(df_log, use_container_width=True)

except Exception as e:
    st.error(f"Could not load data. Check your published URLs or database: {e}")