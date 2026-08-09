import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Season 1 Archive", layout="wide")

st.title("🀄 SEASON 1 ARCHIVE & RECORDS")
st.divider()

# Top Row: Champion & Podium Summary
col_champ, col_podium = st.columns(2)

with col_champ:
    st.subheader("🏆 SEASON 1 CHAMPION")
    st.success("🥇 **John**")

with col_podium:
    st.subheader("🏅 FINAL PODIUM")
    st.markdown("""
    * 🥇 **1st Place:** John
    * 🥈 **2nd Place:** Emily
    * 🥉 **3rd Place:** Victor
    """)

st.divider()

# Section: MVP & Superlatives
st.subheader("⭐ SEASON MVP & STAT LEADERS")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    * 🌟 **MVP Winner:** Presten
    * 💥 **Highest Scoring Hand:** Emily (*Dealer Baiman - 24,000 pts*) & Presten (*Non-Dealer Sanbaiman - 24,000 pts*)
    * 🎯 **Most Wins (1st Place):** Emily (4 Wins)
    * 🛡️ **Best Deal-In Rate:** Presten (6.17% | 5 Deal-Ins)
    """)

with col2:
    st.markdown("""
    * ⚡ **Most Riichi Calls:** Presten (25 Calls)
    * 🎯 **Most Ron Wins:** Victor (20 Rons)
    * 🌊 **Most Tsumo Wins:** Emily & John (8 Tsumos tied)
    * 🧱 **Least 4th Places:** Jess (0 Last-Place Finishes)
    """)

st.divider()

# Section: Season Standings & Player Metrics
st.subheader("📊 Final Season 1 Standings")

# Data 1: Score & Deal-In Rate Table
stats_data = {
    "Rank": [1, 2, 3, 4, 5, 6, 7, 8],
    "Player": [
        "Presten",
        "Thomas",
        "Emily",
        "Victor",
        "John",
        "Jess",
        "Josh",
        "Aaron",
    ],
    "Score": [445.7, 421.3, 401.5, 381.2, 343.1, 247.5, 225.1, 136.0],
    "Deal-In Rate": [
        "6.17%",
        "16.87%",
        "11.25%",
        "11.90%",
        "16.46%",
        "16.25%",
        "20.93%",
        "21.52%",
    ],
}
df_stats = pd.DataFrame(stats_data)

# Data 2: Placement & Live Standings Table
standings_data = {
    "Rank": [1, 2, 3, 4, 5, 6, 7, 8],
    "Player": [
        "Emily",
        "Victor",
        "Presten",
        "John",
        "Thomas",
        "Jess",
        "Aaron",
        "Josh",
    ],
    "Games": [7, 7, 7, 7, 7, 7, 7, 7],
    "1st": [4, 3, 2, 1, 2, 1, 1, 0],
    "2nd": [2, 2, 1, 4, 2, 1, 0, 2],
    "3rd": [0, 0, 3, 1, 2, 5, 2, 1],
    "4th": [1, 2, 1, 1, 1, 0, 4, 4],
    "Points": [151.7, 46.7, 32.8, -4.4, -12.4, -54.4, -219.3, -250.7],
    "Pen.": ["", "", "", "", "", "", "", "-30"],
}
df_standings = pd.DataFrame(standings_data)

tab1, tab2 = st.tabs(["🏆 Regular Season Standings", "📈 Player Performance Metrics"])

with tab1:
    st.dataframe(df_standings, use_container_width=True, hide_index=True)

with tab2:
    st.dataframe(df_stats, use_container_width=True, hide_index=True)