import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="P League Analytics", page_icon="🀄", layout="wide")

# Master Google Sheet Reference
SHEET_ID = "1AVp4aZY85yM7yCfJ9FwgXBIqNRGDj6wqMpoBI2giCPA"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="


@st.cache_data(ttl=60)
def load_season_data():
    roster_df = pd.read_csv(BASE_URL + "Roster", usecols=[0, 1, 2])
    roster_df.columns = ["Name", "Elo", "Hex Color"]
    mvp_df = pd.read_csv(BASE_URL + "MVP_Log")
    game_log_df = pd.read_csv(BASE_URL + "Game_Log")
    return roster_df, mvp_df, game_log_df


@st.cache_data(ttl=60)
def load_all_time_hands():
    try:
        # 1. Read the sheet completely raw (header=None tells Pandas NOT to use the first row as headers)
        df = pd.read_csv(BASE_URL + "All_Time_Hands", header=None)

        # 2. Force the exact, clean headers across the top
        df.columns = ["Round", "Action", "Winner", "Payer", "Points", "Hand", "Dealer", "Riichi's"]


        # this line filters them out so they don't show up as a weird row of data.
        df = df[df["Round"] != "Round"].reset_index(drop=True)

        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_player_profiles():
    # 1. Load Season 1 (Static Archive)
    try:
        s1 = pd.read_csv(BASE_URL + "Season%201%20Hands", usecols=[0, 1, 2, 3, 4, 5])
        s1.columns = ["Round", "Action", "Winner", "Payer", "Points", "Hand"]
        s1["Season"] = "Season 1"
    except Exception:
        s1 = pd.DataFrame()

    # 2. Load Season 2 (Static Archive)
    try:
        s2 = pd.read_csv(BASE_URL + "Season%202%20Hands", usecols=[0, 1, 2, 3, 4, 5])
        s2.columns = ["Round", "Action", "Winner", "Payer", "Points", "Hand"]
        s2["Season"] = "Season 2"
    except Exception:
        s2 = pd.DataFrame()

    # 3. Load Season 3 (Dynamic - Might be empty at the start of a season)
    try:
        s3 = pd.read_csv(BASE_URL + "Season%203%20Hands", skiprows=1, header=None, usecols=[1, 2, 3, 4, 5, 6])
        s3.columns = ["Round", "Action", "Winner", "Payer", "Points", "Hand"]
        s3["Season"] = "Season 3"
    except Exception:
        # If the sheet is empty, create a blank dataframe with the correct columns
        s3 = pd.DataFrame(columns=["Round", "Action", "Winner", "Payer", "Points", "Hand", "Season"])

    # 4. Combine all seasons safely
    all_seasons = pd.concat([s1, s2, s3], ignore_index=True)
    all_seasons['Points'] = pd.to_numeric(all_seasons['Points'], errors='coerce').fillna(0)

    return all_seasons


# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("🀄 P League Hub")
page = st.sidebar.radio(
    "Select a Page:",
    ["Season 3 (Current)", "Player Profiles", "All-Time Hand History", "Season 2 Archive", "Season 1 Archive"]
)

# ==========================================
# PAGE: SEASON 3 (CURRENT)
# ==========================================
if page == "Season 3 (Current)":
    st.title("🀄 P League Analytics Engine - Season 3")
    st.markdown("Live Elo standings, player superlatives, and match history tracking.")

    try:
        roster, mvp_log, match_history = load_season_data()

        # Clean Roster
        roster = roster.dropna(subset=['Name']).reset_index(drop=True)
        roster['Elo'] = pd.to_numeric(roster['Elo'], errors='coerce').round(1)
        roster = roster.sort_values(by="Elo", ascending=False).reset_index(drop=True)

        # Clean MVP Stats
        mvp_log = mvp_log.dropna(subset=['Player Name'])
        int_columns = ["Games Played", "Hands Played", "Ron's", "Tsumo's", "Deal-In's", "Riichi's"]
        for col in int_columns:
            if col in mvp_log.columns:
                mvp_log[col] = pd.to_numeric(mvp_log[col], errors='coerce').fillna(0).astype(int)

        mvp_log['Deal-In Rate Str'] = mvp_log.apply(
            lambda row: f"{(row['Deal-In\'s'] / row['Hands Played'] * 100):.1f}%" if row[
                                                                                         'Hands Played'] > 0 else "0.0%",
            axis=1
        )
        mvp_log['Eligible'] = mvp_log['Games Played'].apply(lambda x: "✅" if x >= 5 else "❌")

        mvp_display = mvp_log[
            ['Player Name', 'Eligible', 'Games Played', "Ron's", "Tsumo's", "Deal-In Rate Str"]].sort_values(
            by="Games Played", ascending=False)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.header("📈 Live Elo Standings")
            st.dataframe(roster[['Name', 'Elo']], hide_index=True, use_container_width=True, height=400)
        with col2:
            st.header("📊 MVP & Superlative Leaders")
            st.dataframe(mvp_display, hide_index=True, use_container_width=True, height=400)

        st.divider()
        st.header("📝 Recent Match History")
        if not match_history.empty:
            st.dataframe(match_history.dropna(how='all').iloc[::-1], hide_index=True, use_container_width=True)
        else:
            st.info("No matches have been logged yet for Season 3.")

    except Exception as e:
        st.error(f"Error loading Season 3 data. Please ensure tabs 'Roster', 'MVP_Log', and 'Game_Log' exist. ({e})")

# ==========================================
# PAGE: PLAYER PROFILES
# ==========================================
elif page == "Player Profiles":
    st.title("👤 Player Profile & Statistics")

    profiles_df = load_player_profiles()

    if not profiles_df.empty:
        # 1. Fetch Unique Players (Filter out Ryuukyoku multi-winners with commas)
        valid_winners = profiles_df.dropna(subset=['Winner'])
        valid_winners = valid_winners[~valid_winners['Winner'].str.contains(',', na=False)]
        player_list = sorted(valid_winners['Winner'].unique().tolist())

        if not player_list:
            st.warning("No single-player stats found.")
            st.stop()

        selected_player = st.selectbox("Select a Player:", player_list)
        st.markdown(f"## All-Time Statistics for **{selected_player}**")

        # 2. Build Wins Dataframe
        wins_df = profiles_df[
            (profiles_df['Winner'] == selected_player) &
            (profiles_df['Action'].isin(['Ron', 'Tsumo'])) &
            (~profiles_df['Winner'].str.contains(',', na=False))
            ]

        # 3. Build Deal-Ins Dataframe
        deal_ins_df = profiles_df[
            (profiles_df['Action'] == 'Ron') &
            (profiles_df['Payer'].str.contains(selected_player, na=False))
            ]

        # --- Display Metrics ---
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("All-Time Wins", len(wins_df))
        col2.metric("All-Time Points Scored", int(wins_df["Points"].sum()))
        col3.metric("All-Time Deal-Ins", len(deal_ins_df))

        highest_hand = wins_df["Points"].max() if not wins_df.empty else 0
        col4.metric("Highest Value Hand", int(highest_hand))

        avg_hand = wins_df["Points"].mean() if not wins_df.empty else 0
        col5.metric("Avg Hand Value", f"{avg_hand:,.0f} pts")

        st.divider()

        # --- Breakdown Tables & Charts ---
        tab1, tab2, tab3 = st.tabs(["Winning Hands History", "Deal-In History", "Season Comparison"])

        with tab1:
            st.subheader("All-Time Winning Hands")
            if not wins_df.empty:
                st.dataframe(wins_df[['Season', 'Action', 'Points', 'Hand']].sort_values(by="Season", ascending=False),
                             hide_index=True, use_container_width=True)
            else:
                st.info("No single-winner hands recorded for this player.")

        with tab2:
            st.subheader("All-Time Direct Deal-Ins")
            if not deal_ins_df.empty:
                st.dataframe(
                    deal_ins_df[['Season', 'Winner', 'Points', 'Hand']].sort_values(by="Season", ascending=False),
                    hide_index=True, use_container_width=True)
            else:
                st.info("No direct deal-ins recorded for this player.")

        with tab3:
            st.subheader("Wins Breakdown by Season")
            if not wins_df.empty:
                season_breakdown = wins_df.groupby("Season").agg(
                    Wins=("Action", "count"),
                    Total_Points=("Points", "sum")
                ).reset_index()

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

# ==========================================
# PAGE: ALL-TIME HAND HISTORY
# ==========================================
elif page == "All-Time Hand History":
    st.title("📚 All-Time Hand Archive")
    st.markdown("A complete, running log of every hand played across all P League seasons.")

    all_hands_df = load_all_time_hands()

    if not all_hands_df.empty:
        # Clean up empty rows
        all_hands_df = all_hands_df.dropna(how='all')

        # Display the massive hand table, reversed so the newest hands are at the top
        st.dataframe(all_hands_df.iloc[::-1], hide_index=True, use_container_width=True, height=700)
    else:
        st.info(
            "⚠️ Could not find the 'All_Time_Hands' tab, or it is currently empty. Make sure the VSTACK formula is working in Google Sheets!")

# ==========================================
# PAGE: SEASON 2 ARCHIVE
# ==========================================
elif page == "Season 2 Archive":
    st.title("🏆 Season 2 Archive & Records")
    st.divider()

    st.subheader("🏆 SEASON 2 CHAMPION")
    st.markdown("🥇 **Eli**")

    st.subheader("🏅 FINAL PODIUM")
    st.markdown("🥇 **1st Place:** Eli  \n🥈 **2nd Place:** Emily  \n🥉 **3rd Place:** Victor")

    st.divider()

    st.subheader("⭐ SEASON MVP & STAT LEADERS")
    st.markdown("""
    - 🌟 **MVP Winner:** Victor
    - 💥 **Highest Scoring Hand:** Aaron (Dealer Counted Yakuman – 48,000 pts)
    - 🎯 **Most Wins (1st):** Victor & Emily (5 Wins tied)
    - 🛡️ **Best Deal-In Rate:** Emily (5.13%)
    - ⚡ **Most Riichi Calls:** Victor, Phonzo, & Thomas (16 Calls tied)
    - 🎯 **Most Ron Wins:** Phonzo & Eli (15 Rons tied)
    - 🌊 **Most Tsumo Wins:** Victor (13 Tsumos)
    - 🧱 **Least 4th Places:** Emily (0 Last-Place Finishes)
    """)

# ==========================================
# PAGE: SEASON 1 ARCHIVE
# ==========================================
elif page == "Season 1 Archive":
    st.title("🏆 Season 1 Archive & Records")
    st.divider()

    st.subheader("🏆 SEASON 1 CHAMPION")
    st.markdown("🥇 **John**")

    st.subheader("🏅 FINAL PODIUM")
    st.markdown("🥇 **1st Place:** John  \n🥈 **2nd Place:** Emily  \n🥉 **3rd Place:** Victor")

    st.divider()

    st.subheader("⭐ SEASON MVP & STAT LEADERS")
    st.markdown("""
    - 🌟 **MVP Winner:** Presten
    - 💥 **Highest Scoring Hand:** Emily (Dealer Baiman – 24,000 pts) & Presten (Non-Dealer Sanbaiman – 24,000 pts)
    - 🎯 **Most Wins (1st):** Emily (4 Wins)
    - 🛡️ **Best Deal-In Rate:** Presten (6.17% | 5 Deal-Ins)
    - ⚡ **Most Riichi Calls:** Presten (25 Calls)
    - 🎯 **Most Ron Wins:** Victor (20 Rons)
    - 🌊 **Most Tsumo Wins:** Emily & John (8 Tsumos tied)
    - 🧱 **Least 4th Places:** Jess (0 Last-Place Finishes)
    """)