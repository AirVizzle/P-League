import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Season 2 Details & Progress", layout="wide")

st.title("🀄 Season 2: Detailed Breakdown")

conn = sqlite3.connect("mahjong_league.db")

# Read tables
try:
    df_hands = pd.read_sql_query("SELECT * FROM season_2_hands", conn)
except Exception:
    df_hands = pd.DataFrame()

try:
    df_schedule = pd.read_sql_query("SELECT * FROM game_log", conn)
except Exception:
    df_schedule = pd.DataFrame()

conn.close()

# Overview Tabs
tab_groups, tab_stats = st.tabs(["👥 Group Assignments", "🎯 Hand Breakdown"])

with tab_groups:
    st.subheader("Season 2 Groups & Table Matchups")
    if not df_schedule.empty:
        if "Group" in df_schedule.columns:
            groups = [
                g
                for g in df_schedule["Group"].unique()
                if pd.notna(g) and str(g).strip() != ""
            ]
            selected_group = st.selectbox(
                "Filter by Group:", ["All Groups"] + groups
            )

            if selected_group != "All Groups":
                filtered_schedule = df_schedule[
                    df_schedule["Group"] == selected_group
                ]
            else:
                filtered_schedule = df_schedule

            st.dataframe(
                filtered_schedule, use_container_width=True, hide_index=True
            )
        else:
            st.dataframe(df_schedule, use_container_width=True, hide_index=True)
    else:
        st.info("No group schedule found in game log.")

with tab_stats:
    st.subheader("Season 2 Hand Statistics")
    if not df_hands.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Action Distribution")
            if "Action" in df_hands.columns:
                action_counts = df_hands["Action"].value_counts().reset_index()
                action_counts.columns = ["Action", "Count"]
                fig_pie = px.pie(
                    action_counts,
                    names="Action",
                    values="Count",
                    title="Hand Outcomes Ratio",
                    hole=0.4,
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("### High Scoring Hands")
            if "Points" in df_hands.columns and "Winner" in df_hands.columns:
                top_hands = df_hands.sort_values(
                    by="Points", ascending=False
                ).head(10)
                st.dataframe(
                    top_hands[["Winner", "Action", "Points", "Hand"]],
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.info("Hand stats will generate as games are logged in Season 2.")