import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="Mahjong League - Home", layout="wide")

# 2. Google Sheets Published CSV Links
SEASON_1_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=170190578&single=true&output=csv"
SEASON_2_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=983730091&single=true&output=csv"
GAME_LOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=721192921&single=true&output=csv"

# Published CSV link for your MVP tab
MVP_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRARMn8tXHFhuNzBEAuaUYdj770g60dKypHCbOsEiwI-uzHPoew_1dXekL5DGjslzt0bb5pr1BiTVu5/pub?gid=1774839977&single=true&output=csv"

# Conference Rosters
EAST_PLAYERS = ["Victor", "John", "Emily", "Presten", "Thomas", "Eli"]
SOUTH_PLAYERS = ["Tyler", "Jess", "Aaron", "Phonzo", "George", "Josh"]
ALL_PLAYERS = EAST_PLAYERS + SOUTH_PLAYERS


# 3. Load Data directly from Google Sheets (In-Memory Fetching)
@st.cache_data(ttl=60)
def fetch_sheet_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


# 4. Helper Function: Calculate Standings & Placements from Game Log (Standard +30/+10/-10/-30 Net Uma)
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

    UMA_TIERS = [30.0, 10.0, -10.0, -30.0]

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

                    for rank_idx, (p_name, raw_score) in enumerate(game_players):
                        net_uma = ((raw_score - 30000.0) / 1000.0) + UMA_TIERS[rank_idx]

                        stats[p_name]["Games"] += 1
                        stats[p_name]["Uma / Points"] += net_uma
                        stats[p_name][placements[rank_idx]] += 1

    df = pd.DataFrame.from_dict(stats, orient="index")
    df = df.rename_axis("Player").reset_index()

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


# 5. Helper Function: Process Raw MVP Table directly from Google Sheet
def load_raw_mvp_data(df_mvp_raw):
    if not df_mvp_raw.empty and len(df_mvp_raw) > 0:
        df_mvp = df_mvp_raw.copy()

        col_map = {
            "Total MVP Score": "Score",
            "MVP Score": "Score",
            "Deal-in Rate": "Deal-In Rate",
            "Deal In Rate": "Deal-In Rate"
        }
        df_mvp = df_mvp.rename(columns=col_map)

        if "Score" in df_mvp.columns:
            df_mvp["Score"] = pd.to_numeric(df_mvp["Score"], errors="coerce").fillna(0.0)
            df_mvp.sort_values(by="Score", ascending=False, inplace=True)

        if "Deal-In Rate" in df_mvp.columns:
            df_mvp["Deal-In Rate"] = df_mvp["Deal-In Rate"].astype(str).apply(
                lambda x: f"{x.strip().replace('%', '')}%" if x.strip() not in ["", "nan", "None"] else "0.00%"
            )
            df_mvp["DealInRate_Num"] = (
                df_mvp["Deal-In Rate"]
                .str.replace("%", "", regex=False)
            )
            df_mvp["DealInRate_Num"] = pd.to_numeric(df_mvp["DealInRate_Num"], errors="coerce").fillna(0.0)
        else:
            df_mvp["Deal-In Rate"] = "0.00%"
            df_mvp["DealInRate_Num"] = 0.0

        df_mvp.reset_index(drop=True, inplace=True)

        if "Rank" not in df_mvp.columns:
            df_mvp["Rank"] = df_mvp.index + 1
        else:
            df_mvp["Rank"] = pd.to_numeric(df_mvp["Rank"], errors="coerce").fillna(df_mvp.index + 1).astype(int)

        return df_mvp

    return pd.DataFrame()


# 6. Helper Function: Generate Dynamic Weekly Ticker
@st.cache_data(ttl=60)
def get_week_ticker_text():
    try:
        df = fetch_sheet_data(GAME_LOG_URL)
        if df.empty:
            return "🀄 Welcome to P League! Check match details in the schedule tab."

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
                p1, s1 = row.get("Player 1", ""), int(float(row.get("Score 1", 0)))
                p2, s2 = row.get("Player 2", ""), int(float(row.get("Score 2", 0)))
                p3, s3 = row.get("Player 3", ""), int(float(row.get("Score 3", 0)))
                p4, s4 = row.get("Player 4", ""), int(float(row.get("Score 4", 0)))

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

    df_s2_hands = fetch_sheet_data(SEASON_2_URL)
    df_log = fetch_sheet_data(GAME_LOG_URL)
    df_mvp_raw = fetch_sheet_data(MVP_URL)

    # Calculate Full Standings & MVP Stats
    s2_leaderboard = calculate_standings_from_game_log(df_log)
    df_mvp = load_raw_mvp_data(df_mvp_raw)

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

    int_col_config = {
        "1st": st.column_config.NumberColumn(format="%d"),
        "2nd": st.column_config.NumberColumn(format="%d"),
        "3rd": st.column_config.NumberColumn(format="%d"),
        "4th": st.column_config.NumberColumn(format="%d"),
        "Games": st.column_config.NumberColumn(format="%d"),
        "Uma / Points": st.column_config.NumberColumn(format="%+.1f"),
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

        if not df_mvp.empty:
            mvp_leader = df_mvp.iloc[0]
            least_dealins = df_mvp.sort_values(by="DealInRate_Num", ascending=True).iloc[0]

            m_col1, m_col2 = st.columns(2)
            m_col1.metric(
                "⭐ MVP Leader",
                f"{mvp_leader['Player']}",
                f"{mvp_leader['Score']:.1f} pts",
            )
            m_col2.metric(
                "🛡️ Lowest Deal-In Rate",
                f"{least_dealins['Player']}",
                f"{least_dealins['Deal-In Rate']} Rate",
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
                if not df_mvp.empty:
                    display_cols = [c for c in ["Rank", "Player", "Score", "Deal-In Rate"] if c in df_mvp.columns]
                    st.dataframe(
                        df_mvp[display_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Rank": st.column_config.NumberColumn(format="%d"),
                            "Player": st.column_config.TextColumn("Player"),
                            "Score": st.column_config.NumberColumn(
                                "Score", format="%.1f"
                            ),
                            "Deal-In Rate": st.column_config.TextColumn(
                                "Deal-In Rate"
                            ),
                        },
                    )
                else:
                    st.info(
                        "⭐ MVP standings will display here once MVP_URL is updated."
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
        st.subheader("Recent Season 2 Hands (Newest First)")
        if not df_s2_hands.empty:
            recent_hands = df_s2_hands.tail(10).iloc[::-1]
            st.dataframe(recent_hands, use_container_width=True, hide_index=True)

            if "Action" in df_s2_hands.columns:
                st.subheader("Hand Outcomes Overview")
                action_counts = (
                    df_s2_hands["Action"]
                    .value_counts()
                    .reset_index()
                )

                fig_actions = px.bar(
                    action_counts,
                    x=action_counts.columns[0],
                    y=action_counts.columns[1],
                    color=action_counts.columns[0],
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
    st.error(f"Could not load data. Check your published URLs: {e}")