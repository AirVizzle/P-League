import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Match Results & Logs", layout="wide")

st.title("🎮 Season 2 Match Results & Game Logs")

conn = sqlite3.connect("mahjong_league.db")

try:
    df_games = pd.read_sql_query("SELECT * FROM game_log", conn)
except Exception:
    df_games = pd.DataFrame()

conn.close()

if df_games.empty:
    st.info("No game log data available yet.")
    st.stop()

# Clean column headers
df_games.columns = df_games.columns.str.strip()

# Separate Completed Games from Scheduled/TBA Games
if "Score 1" in df_games.columns:
    completed_games = df_games[
        df_games["Score 1"].notna()
        & (df_games["Score 1"].astype(str).str.strip() != "")
    ].copy()
else:
    completed_games = pd.DataFrame()

# Top Metric Highlights
col1, col2, col3 = st.columns(3)
col1.metric("Matches Completed", len(completed_games))
col2.metric("Total Scheduled", len(df_games))
col3.metric(
    "Remaining Matches", max(0, len(df_games) - len(completed_games))
)

st.divider()

# Layout Tabs
tab_log, tab_charts = st.tabs(["📋 Completed Match Logs", "📈 Match Visuals"])

with tab_log:
    st.subheader("Official Match Scores")
    if not completed_games.empty:
        # Display clean table of completed matches
        st.dataframe(completed_games, use_container_width=True, hide_index=True)
    else:
        st.info("No matches have been completed yet for Season 2.")

with tab_charts:
    st.subheader("Game Score Distributions")
    if not completed_games.empty:
        # Reshape data to plot scores player by player for each completed game
        plot_data = []
        for _, row in completed_games.iterrows():
            game_id = f"Game {row.get('Game ID', '?')} ({row.get('Group', '')})"
            for i in [1, 2, 3, 4]:
                player = row.get(f"Player {i}")
                score = row.get(f"Score {i}")
                if pd.notna(player) and pd.notna(score):
                    try:
                        plot_data.append(
                            {
                                "Game": game_id,
                                "Player": str(player).strip(),
                                "Score": float(score),
                            }
                        )
                    except ValueError:
                        pass

        if plot_data:
            df_plot = pd.DataFrame(plot_data)

            # Interactive Plotly Bar Chart comparing player scores per match
            fig = px.bar(
                df_plot,
                x="Game",
                y="Score",
                color="Player",
                barmode="group",
                title="Match-by-Match Score Breakdown",
                text="Score",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log numeric scores in your sheet to generate match charts!")
    else:
        st.info("Match visual trends will generate here as scores are logged.")