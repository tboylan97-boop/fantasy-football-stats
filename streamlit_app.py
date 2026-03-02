import streamlit as st
import pandas as pd
import plotly.express as px

# Page Configuration
st.set_page_config(page_title="The Ultimate League Site", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Load Draft Data
    draft_df = pd.read_excel('Draft Data GPT (1).xlsx')
    
    # Load Game History (Using the 'Every Game' sheet)
    # Ensure this filename matches your GitHub file
    history_df = pd.read_excel('OFFICIAL Every Game GPT.xlsx', sheet_name='Every Game')
    
    return draft_df, history_df

try:
    draft_df, history_df = load_data()

    # --- NAVIGATION ---
    st.sidebar.title("🎮 Navigation")
    page = st.sidebar.radio("Go to:", ["Draft Room", "League Records", "Head-to-Head"])

    # --- GLOBAL FILTERS ---
    st.sidebar.divider()
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)

    # ==========================================
    # PAGE 1: DRAFT ROOM
    # ==========================================
    if page == "Draft Room":
        st.title(f"🎯 Draft Room: {selected_owner}")
        
        owner_draft = draft_df[draft_df['Owner'] == selected_owner]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Avg Draft ROI", f"{owner_draft['ROI Score'].mean():.1f}")
        m2.metric("Best Pick", owner_draft.sort_values("ROI Score", ascending=False).iloc[0]['Player Name'])
        m3.metric("Total Pts Drafted", f"{owner_draft['Points'].sum():,.0f}")

        fig = px.scatter(owner_draft, x="Round", y="ROI Score", color="ROI Tier", 
                         hover_data=["Player Name", "Year"], title="Draft Value over Time")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(owner_draft[['Year', 'Round', 'Player Name', 'ROI Tier', 'Points']], use_container_width=True)

    # ==========================================
    # PAGE 2: LEAGUE RECORDS
    # ==========================================
    elif page == "League Records":
        st.title(f"📈 Career Stats: {selected_owner}")
        
        owner_games = history_df[history_df['Owner'] == selected_owner]
        
        # Calculate Win/Loss
        wins = len(owner_games[owner_games['Result'] == 'Win'])
        losses = len(owner_games[owner_games['Result'] == 'Loss'])
        ties = len(owner_games[owner_games['Result'] == 'Tie'])
        win_pct = (wins / (wins + losses)) * 100 if (wins+losses) > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("All-Time Record", f"{wins}-{losses}-{ties}")
        c2.metric("Win %", f"{win_pct:.1f}%")
        c3.metric("Total Points For", f"{owner_games['Points'].sum():,.1f}")
        c4.metric("Avg Points/Game", f"{owner_games['Points'].mean():.1f}")

        # Points Trend
        st.subheader("Points Scored by Season")
        season_pts = owner_games.groupby('Year')['Points'].sum().reset_index()
        fig_trend = px.line(season_pts, x='Year', y='Points', markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

    # ==========================================
    # PAGE 3: HEAD-TO-HEAD
    # ==========================================
    elif page == "Head-to-Head":
        st.title("⚔️ Rivalry Breakdown")
        
        opponent = st.selectbox("Select Rival", [o for o in all_owners if o != selected_owner])
        
        # Filter for games between these two
        rivalry_df = history_df[(history_df['Owner'] == selected_owner) & (history_df['Opponent'] == opponent)]
        
        r_wins = len(rivalry_df[rivalry_df['Result'] == 'Win'])
        r_losses = len(rivalry_df[rivalry_df['Result'] == 'Loss'])
        
        st.subheader(f"{selected_owner} vs {opponent}")
        st.write(f"### Record: {r_wins} Wins - {r_losses} Losses")
        
        # Progress bar for visual win ratio
        progress = r_wins / (r_wins + r_losses) if (r_wins + r_losses) > 0 else 0.5
        st.progress(progress)
        
        st.dataframe(rivalry_df[['Year', 'Week', 'Points', 'Points Against', 'Result', 'Difference']], use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Check that 'OFFICIAL Every Game GPT.xlsx' and 'Draft Data GPT (1).xlsx' are in GitHub.")
