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

# Conference Rosters
EAST_PLAYERS = ["Victor", "John", "Emily", "Presten", "Thomas", "Eli"]
SOUTH_PLAYERS = ["Tyler", "Jess", "Aaron", "Phonzo", "George", "Josh"]
ALL_PLAYERS = EAST_PLAYERS + SOUTH_PLAYERS

# MVP Calculation Weights
MVP_WEIGHTS = {
    "riichi": 8,
    "tsumo": 15,
    "ron": 12,
    "dealInMultiplier": 200,  # (rate * 100 * 2)
}


# 3. Load & Sync Data into SQLite
@st.cache_data(ttl=60)
def load_and_sync_data():
    conn = sqlite3.connect("mahjong_league.db")

    try:
        pd.read_csv(SEASON_1_URL).to_sql(
            "season_1_hands", conn, if_exists="replace", index=False
        )
    except Exception as e:
        st.warning(f"Could not load Season 1 data: {e}")

    try:
        pd.read_csv(SEASON_2_URL).to_sql(
            "season_2_hands", conn, if_exists="replace", index=False
        )
    except Exception as e:
        st.warning(f"Could not load Season 2 data: {e}")

    try:
        df_game_log = pd.read_csv(GAME_LOG_URL)
        df_game_log.columns = df_game_log.columns.str.strip()
        df_game_log.to_sql("game_log", conn, if_exists="replace", index=False)
    except Exception as e:
        st.warning(f"Could not load Game Log data: {e}")

    conn.close()
    return True


# 4. Helper Function: Calculate Standings & Placements from Game Log
def calculate_standings_from_game_log(df_log):
    stats = {
        p: {
            "Games": 0,
            "1st": 0,
            "2nd": 0,
            "3rd": 0,
            "4th": 0,
            "Uma / Points": 0.0,
        }
        for p in ALL_PLAYERS
    }

    if not df_log.empty and "Score 1" in df_log.columns:
        for _, row in df_log.iterrows():
            score_1 = str(row.get("Score 1", "")).strip()
            if (
                pd.notna(row.get("Score 1"))
                and score_1 not in ["", "nan"]
                and score_1 != "0"
            ):
                game_players = []
                for i in range(1, 5):
                    p = str(row.get(f"Player {i}", "")).strip()
                    try:
                        s = float(row.get(f"Score {i}", 0))
                    except ValueError:
                        s = 0.0
                    if p and p in stats:
                        game_players.append((p, s))

                if len(game_players) == 4:
                    game_players.sort(key=lambda x: x[1], reverse=True)
                    placements = ["1st", "2nd", "3rd", "4th"]

                    for rank_idx, (p_name, score) in enumerate(game_players):
                        stats[p_name]["Games"] += 1
                        stats[p_name]["Uma / Points"] += score
                        stats[p_name][placements[rank_idx]] += 1

    df = pd.DataFrame.from_dict(stats, orient="index").reset_index()
    df.rename(columns={"index": "Player"}, inplace=True)

    df["Conference"] = df["Player"].apply(
        lambda x: "East"
        if x in EAST_PLAYERS
        else ("South" if x in SOUTH_PLAYERS else "Other")
    )

    df.sort_values(
        by=["Uma / Points", "1st", "2nd"], ascending=False, inplace=True
    )
    df.reset_index(drop=True, inplace=True)
    return df


# 5. Helper Function: Calculate MVP & Category Leaders from Hand Logs
def calculate_leaders_and_mvp(df_hands):
    mvp_stats = {
        p: {"riichi": 0, "tsumo": 0, "ron": 0, "dealIns": 0, "hands": 0}
        for p in ALL_PLAYERS
    }

    if not df_hands.empty:
        # Standardize column names
        df_hands.columns = df_hands.columns.str.strip()

        for _, row in df_hands.iterrows():
            action = str(row.get("Action", "")).strip()
            winner = str(row.get("Winner", "")).strip()
            payer = str(row.get("Payer", "")).strip()
            riichi_caller = str(row.get("Riichi", "")).strip()

            # Track Riichi Calls
            if riichi_caller and riichi_caller in mvp_stats:
                mvp_stats[riichi_caller]["riichi"] += 1

            # Track Wins & Deals
            if action == "Ron":
                if winner in mvp_stats:
                    mvp_stats[winner]["ron"] += 1
                if payer in mvp_stats:
                    mvp_stats[payer]["dealIns"] += 1
            elif action == "Tsumo":
                if winner in mvp_stats:
                    mvp_stats[winner]["tsumo"] += 1

            # Count overall active hands per player
            for p in ALL_PLAYERS:
                mvp_stats[p]["hands"] += 1

    df_mvp = pd.DataFrame.from_dict(mvp_stats, orient="index").reset_index()
    df_mvp.rename(columns={"index": "Player"}, inplace=True)

    # Calculate Deal-In Rate & MVP Score
    df_mvp["DealInRate"] = df_mvp.apply(
        lambda r: (r["dealIns"] / r["hands"]) if r["hands"] > 0 else 0.0, axis=1
    )

    df_mvp["MVP Score"] = (
        (df_mvp["riichi"] * MVP_WEIGHTS["riichi"])
        + (df_mvp["tsumo"] * MVP_WEIGHTS["tsumo"])
        + (df_mvp["ron"] * MVP_WEIGHTS["ron"])
        - (df_mvp["DealInRate"] * MVP_WEIGHTS["dealInMultiplier"])
    )

    df_mvp.sort_values(by="MVP Score", ascending=False, inplace=True)
    df_mvp.reset_index(drop=True, inplace=True)
    df_mvp["Rank"] = df_mvp.index + 1

    return df_mvp


# 6. Helper Function: Generate Dynamic Weekly Ticker (Auto-Detects Latest Week & Strips Decimals)
@st.cache_data(ttl=60)
def get_week_ticker_text():
    try:
        df = pd.read_csv(GAME_LOG_URL)
        df.columns = df.columns.str.strip()
        ticker_items = []

        if "Week" in df.columns and not df["Week"].dropna().empty:
            target_week = df["Week"].dropna().iloc[-1]
            week_games = df[df["Week"] == target_week]
        else:
            target_week = "Latest Matches"
            week_games = df

        for _, row in week_games.iterrows():
            group = (
                row.get("Group", "Match") if "Group" in df.columns else "Match"
            )
            score_1 = str(row.get("Score 1", "")).strip()

            if pd.notna(row.get("Score 1")) and score_1 not in ["", "nan"]:
                p1, s1 = row.get("Player 1", ""), int(
                    float(row.get("Score 1", 0))
                )
                p2, s2 = row.get("Player 2", ""), int(
                    float(row.get("Score 2", 0))
                )
                p3, s3 = row.get("Player 3", ""), int(
                    float(row.get("Score 3", 0))
                )
                p4, s4 = row.get("Player 4", ""), int(
                    float(row.get("Score 4", 0))
                )

                match_str = f"🏆 [{target_week} - {group} Result]: {p1} ({s1}) | {p2} ({s2}) | {p3} ({s3}) | {p4} ({s4})"
            else:
                players = [
                    str(row.get(f"Player {i}")).strip()
                    for i in range(1, 5)
                    if pd.notna(row.get(f"Player {i}"))
                    and str(row.get(f"Player {i}")).strip() not in ["", "nan"]
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
    load_and_sync_data()

    # Ticker HTML (Auto-Detects Latest Week)
    ticker_text = get_week_ticker_text()
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

    st.title("🀄 Mahjong League Dashboard")

    conn = sqlite3.connect("mahjong_league.db")

    try:
        df_s2_hands = pd.read_sql_query("SELECT * FROM season_2_hands", conn)
        if "Points" in df_s2_hands.columns:
            df_s2_hands["Points"] = (
                pd.to_numeric(df_s2_hands["Points"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
    except Exception:
        df_s2_hands = pd.DataFrame()

    try:
        df_log = pd.read_sql_query("SELECT * FROM game_log", conn)
    except Exception:
        df_log = pd.DataFrame()

    conn.close()

    # Calculate Full Standings & MVP Stats
    s2_leaderboard = calculate_standings_from_game_log(df_log)
    df_mvp = calculate_leaders_and_mvp(df_s2_hands)

    # Filter into East and South Conferences
    east_df = (
        s2_leaderboard[s2_leaderboard["Conference"] == "East"]
        .drop(columns=["Conference"])
        .reset_index(drop=True)
    )
    south_df = (
        s2_leaderboard[s2_leaderboard["Conference"] == "South"]
        .drop(columns=["Conference"])
        .reset_index(drop=True)
    )
    overall_df = s2_leaderboard.drop(columns=["Conference"]).reset_index(
        drop=True
    )

    # Standard Column Formatters to drop decimals from integers
    int_col_config = {
        "1st": st.column_config.NumberColumn(format="%d"),
        "2nd": st.column_config.NumberColumn(format="%d"),
        "3rd": st.column_config.NumberColumn(format="%d"),
        "4th": st.column_config.NumberColumn(format="%d"),
        "Games": st.column_config.NumberColumn(format="%d"),
    }

    # --- Live Metric Cards ---
    col1, col2, col3 = st.columns(3)
    total_hands_count = len(df_s2_hands) if not df_s2_hands.empty else 0
    leader_name = (
        overall_df.iloc[0]["Player"] if not overall_df.empty else "N/A"
    )
    top_score_val = (
        overall_df.iloc[0]["Uma / Points"] if not overall_df.empty else 0.0
    )

    col1.metric("Season 2 Total Hands", total_hands_count)
    col2.metric("Current Leader", leader_name)
    col3.metric("Top Score", f"{top_score_val:+.1f}")

    st.divider()

    # --- Main Dashboard Tabs ---
    tab_standings, tab_hands, tab_schedule = st.tabs(
        ["🏆 Live Standings", "📊 Season 2 Hands", "📅 Match Log"]
    )

    with tab_standings:
        # --- 👑 LEADING STATISTICS CARDS ---
        st.subheader("👑 League Category Leaders")

        most_rons = df_mvp.sort_values(by="ron", ascending=False).iloc[0]
        most_tsumos = df_mvp.sort_values(by="tsumo", ascending=False).iloc[0]
        most_riichis = df_mvp.sort_values(by="riichi", ascending=False).iloc[0]
        least_dealins = df_mvp.sort_values(
            by="DealInRate", ascending=True
        ).iloc[0]

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric(
            "🀄 Most Rons",
            f"{most_rons['Player']}",
            f"{int(most_rons['ron'])} Wins",
        )
        m_col2.metric(
            "🌕 Most Tsumos",
            f"{most_tsumos['Player']}",
            f"{int(most_tsumos['tsumo'])} Wins",
        )
        m_col3.metric(
            "⚡ Most Riichis",
            f"{most_riichis['Player']}",
            f"{int(most_riichis['riichi'])} Calls",
        )
        m_col4.metric(
            "🛡️ Lowest Deal-In Rate",
            f"{least_dealins['Player']}",
            f"{least_dealins['DealInRate']*100:.2f}% Rate",
        )

        st.markdown("---")

        left_col, right_col = st.columns([1.3, 0.7])

        with left_col:
            st.subheader("🏆 Season 2 Standings")

            tab_overall, tab_east, tab_south, tab_mvp = st.tabs(
                [
                    "🌐 Overall League",
                    "🀀 East Conference",
                    "🀁 South Conference",
                    "⭐ MVP Race",
                ]
            )

            with tab_overall:
                st.dataframe(
                    overall_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config=int_col_config,
                )

            with tab_east:
                st.dataframe(
                    east_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config=int_col_config,
                )

            with tab_south:
                st.dataframe(
                    south_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config=int_col_config,
                )

            with tab_mvp:
                st.dataframe(
                    df_mvp[
                        [
                            "Rank",
                            "Player",
                            "MVP Score",
                            "DealInRate",
                            "ron",
                            "tsumo",
                            "riichi",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Rank": st.column_config.NumberColumn(format="%d"),
                        "MVP Score": st.column_config.NumberColumn(
                            "MVP Score", format="%.1f pts"
                        ),
                        "DealInRate": st.column_config.NumberColumn(
                            "Deal-In Rate", format="%.2f%%"
                        ),
                        "ron": st.column_config.NumberColumn(
                            "Rons", format="%d"
                        ),
                        "tsumo": st.column_config.NumberColumn(
                            "Tsumos", format="%d"
                        ),
                        "riichi": st.column_config.NumberColumn(
                            "Riichis", format="%d"
                        ),
                    },
                )

        with right_col:
            st.subheader("📊 Points Breakdown")
            fig = px.bar(
                overall_df,
                x="Player",
                y="Uma / Points",
                color="Player",
                title="Total League Net Uma",
            )
            st.plotly_chart(fig, use_container_width=True)

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
            st.dataframe(
                df_log,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score 1": st.column_config.NumberColumn(format="%d"),
                    "Score 2": st.column_config.NumberColumn(format="%d"),
                    "Score 3": st.column_config.NumberColumn(format="%d"),
                    "Score 4": st.column_config.NumberColumn(format="%d"),
                },
            )
        else:
            st.info("No match log data found.")

except Exception as e:
    st.error(f"Could not load data. Check your published URLs or database: {e}")