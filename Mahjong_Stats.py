import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="Mahjong League - Home", layout="wide")

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
        df_game_log.columns = df_game_log.columns.str.strip()
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
        df.columns = df.columns.str.strip()
        ticker_items = []

        week_games = (
            df[df["Week"] == target_week] if "Week" in df.columns else df
        )

        for _, row in week_games.iterrows():
            group = (
                row.get("Group", "Match") if "Group" in df.columns else "Match"
            )
            score_1 = str(row.get("Score 1", "")).strip()

            if pd.notna(row.get("Score 1")) and score_1 not in ["", "nan"]:
                p1, s1 = row.get("Player 1", ""), row.get("Score 1", 0)
                p2, s2 = row.get("Player 2", ""), row.get("Score 2", 0)
                p3, s3 = row.get("Player 3", ""), row.get("Score 3", 0)
                p4, s4 = row.get("Player 4", ""), row.get("Score 4", 0)

                match_str = f"🏆 [{target_week} - {group} Result]: {p1} ({s1}) | {p2} ({s2}) | {p3} ({s3}) | {p4} ({s4})"
            else:
                players = []
                for i in [1, 2, 3, 4]:
                    col_name = f"Player {i}"
                    val = row.get(col_name)
                    if pd.notna(val) and str(val).strip() not in ["", "nan"]:
                        players.append(str(val).strip())

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
        return f"🀄 Welcome to P League! Check match details in the schedule tab."


# --- App Execution ---
try:
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

    conn = sqlite3.connect("mahjong_league.db")


        # Fetch Season 2 Standings (Includes ALL scheduled players at 0 pts before games start)
    leaderboard_query = """
        WITH AllPlayers AS (
            SELECT DISTINCT `Player 1` AS Player FROM game_log WHERE `Player 1` IS NOT NULL AND `Player 1` != ''
            UNION
            SELECT DISTINCT `Player 2` AS Player FROM game_log WHERE `Player 2` IS NOT NULL AND `Player 2` != ''
            UNION
            SELECT DISTINCT `Player 3` AS Player FROM game_log WHERE `Player 3` IS NOT NULL AND `Player 3` != ''
            UNION
            SELECT DISTINCT `Player 4` AS Player FROM game_log WHERE `Player 4` IS NOT NULL AND `Player 4` != ''
        )
        SELECT 
            p.Player,
            COALESCE(COUNT(h.Winner), 0) AS Single_Wins,
            COALESCE(SUM(h.Points), 0) AS Total_Points
        FROM AllPlayers p
        LEFT JOIN season_2_hands h 
               ON p.Player = h.Winner 
              AND h.Action IN ('Ron', 'Tsumo') 
              AND h.Winner NOT LIKE '%,%'
        GROUP BY p.Player
        ORDER BY Total_Points DESC, p.Player ASC;
    """
    

    try:
        s2_leaderboard = pd.read_sql_query(leaderboard_query, conn)
    except Exception:
        s2_leaderboard = pd.DataFrame()

    try:
        df_s2_hands = pd.read_sql_query("SELECT * FROM season_2_hands", conn)
    except Exception:
        df_s2_hands = pd.DataFrame()

    try:
        df_log = pd.read_sql_query("SELECT * FROM game_log", conn)
    except Exception:
        df_log = pd.DataFrame()

    conn.close()

    # --- Live Metric Cards ---
    col1, col2, col3 = st.columns(3)
    total_hands_count = len(df_s2_hands) if not df_s2_hands.empty else 0
    leader_name = (
        s2_leaderboard.iloc[0]["Player"] if not s2_leaderboard.empty else "N/A"
    )
    top_score_val = (
        s2_leaderboard.iloc[0]["Total_Points"]
        if not s2_leaderboard.empty
        else 0
    )

    col1.metric("Season 2 Total Hands", total_hands_count)
    col2.metric("Current Leader", leader_name)
    col3.metric("Top Score", top_score_val)

    st.divider()

    # --- Main Dashboard Tabs ---
    tab_standings, tab_hands, tab_schedule = st.tabs(
        ["🏆 Live Standings", "📊 Season 2 Hands", "📅 Match Log"]
    )

    with tab_standings:
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.subheader("🏆 Season 2 Standings")
            if not s2_leaderboard.empty:
                st.dataframe(
                    s2_leaderboard, use_container_width=True, hide_index=True
                )
            else:
                st.info(
                    "Season 2 games haven't been logged yet or database is syncing!"
                )

        with right_col:
            st.subheader("📊 Points Breakdown")
            if not s2_leaderboard.empty:
                fig = px.bar(
                    s2_leaderboard,
                    x="Player",
                    y="Total_Points",
                    color="Player",
                    title="Points Scored",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Standings chart will appear as games are logged.")

    with tab_hands:
        st.subheader("Recent Season 2 Hands")
        if not df_s2_hands.empty:
            st.dataframe(df_s2_hands.head(10), use_container_width=True)

            if "Action" in df_s2_hands.columns:
                st.subheader("Hand Outcomes Overview")
                action_counts = (
                    df_s2_hands["Action"].value_counts().reset_index()
                )
                action_counts.columns = ["Action", "Count"]

                fig_actions = px.bar(
                    action_counts,
                    x="Action",
                    y="Count",
                    color="Action",
                    title="Total Actions Played (Season 2)",
                )
                st.plotly_chart(fig_actions, use_container_width=True)
        else:
            st.info("No Season 2 hand data found.")

    with tab_schedule:
        st.subheader("Match Log & Upcoming Tables")
        if not df_log.empty:
            st.dataframe(df_log, use_container_width=True, hide_index=True)
        else:
            st.info("No match log data found.")

except Exception as e:
    st.error(f"Could not load data. Check your published URLs or database: {e}")