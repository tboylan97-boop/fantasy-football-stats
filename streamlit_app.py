import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup
st.set_page_config(page_title="Draft Room Analytics", layout="wide")

# 2. Data Loading
@st.cache_data
def load_data():
    # Using the Excel file you uploaded to GitHub
    df = pd.read_excel('Draft Data GPT (1).xlsx')
    return df

try:
    draft_df = load_data()

    # 3. Sidebar - Manager Selection
    st.sidebar.title("League Archive")
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select a Manager", all_owners)

    # 4. Filter Data for the Selected Owner
    owner_df = draft_df[draft_df['Owner'] == selected_owner]

    st.title(f"🎯 Draft Room: {selected_owner}")

    # ==========================================
    # PRE-CALCULATING LEAGUE RANKINGS
    # ==========================================
    # We calculate these for everyone so we can see where the selected owner ranks
    
    # Avg Age Ranking
    league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
    age_rank = league_age.index.get_loc(selected_owner) + 1

    # Avg Pick Ranking
    league_picks = draft_df.groupby('Owner')['Pick'].mean().sort_values()
    pick_rank = league_picks.index.get_loc(selected_owner) + 1

    # ==========================================
    # TOP ROW: THE BIG STATS
    # ==========================================
    st.subheader("Draft Resume")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_drafts = owner_df['Year'].nunique()
        st.metric("Total # of Drafts", total_drafts)

    with col2:
        total_picks = len(owner_df)
        st.metric("Total # of Picks", total_picks)

    with col3:
        avg_pick = owner_df['Pick'].mean()
        st.metric("Average Draft Pick", f"{avg_pick:.1f}", f"Rank: {pick_rank}/{len(league_picks)}")

    with col4:
        avg_age = owner_df['Age When Drafted'].mean()
        st.metric("Avg Player Age", f"{avg_age:.1f}", f"Rank: {age_rank}/{len(league_age)}")

    st.divider()

    # ==========================================
    # CHART: DRAFT SLOT HISTORY
    # ==========================================
    st.subheader("Historical Draft Slot (Round 1)")
    # Get only Round 1 picks to show their "Draft Slot" for that year
    slots_df = owner_df[owner_df['Round'] == 1].sort_values('Year')
    
    fig_slots = px.bar(
        slots_df, 
        x='Year', 
        y='Pick', 
        text='Pick',
        title="What pick did you have in the 1st Round?",
        color_discrete_sequence=['#3b82f6']
    )
    # Reverse Y-axis because Pick 1 is "Better" (higher) than Pick 12
    fig_slots.update_yaxes(autorange="reversed", title="Pick Number")
    st.plotly_chart(fig_slots, use_container_width=True)

    # ==========================================
    # TEAMS & POSITIONS
    # ==========================================
    st.divider()
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Most Drafted NFL Teams")
        # Count all 32 teams from highest to lowest
        team_counts = owner_df['Team'].value_counts().reset_index()
        team_counts.columns = ['NFL Team', 'Count']
        
        fig_teams = px.bar(
            team_counts, 
            y='NFL Team', 
            x='Count
