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
    # LOGIC: CALCULATING DRAFT SLOTS (ROUND 1 ONLY)
    # ==========================================
    # This identifies the "Draft Slot" (1-12) for every manager in every year
    # We take the first pick they made in Round 1 for each year
    slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
    
    # Calculate the Average Draft Slot for every owner in the league
    league_avg_slots = slots_df.groupby('Owner')['Pick'].mean().sort_values()
    
    # Get stats for the specific selected owner
    owner_avg_slot = league_avg_slots[selected_owner]
    # Rank: 1 = lowest avg pick (often drafts early), 12 = highest (often drafts late)
    pick_rank = league_avg_slots.index.get_loc(selected_owner) + 1

    # League Age Ranking (for the metric below)
    league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
    age_rank = league_age.index.get_loc(selected_owner) + 1

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
        # This now shows the 1-12 style average
        st.metric("Average Draft Pick", f"{owner_avg_slot:.1f}", f"Rank: {pick_rank}/{len(league_avg_slots)}")

    with col4:
        avg_age = owner_df['Age When Drafted'].mean()
        st.metric("Avg Player Age", f"{avg_age:.1f}", f"Rank: {age_rank}/{len(league_age)}")

    st.divider()

    # ==========================================
    # CHART: DRAFT SLOT HISTORY
    # ==========================================
    st.subheader("Historical Draft Slot (Round 1)")
    owner_slots = slots_df[slots_df['Owner'] == selected_owner].sort_values('Year')
    
    fig_slots = px.bar(
        owner_slots, 
        x='Year', 
        y='Pick', 
        text='Pick',
        title="What pick did you have in the 1st Round?",
        color_discrete_sequence=['#3b82f6']
    )
    # Reverse Y-axis because Pick 1 is "Better" than Pick 12
    fig_slots.update_yaxes(autorange="reversed", title="Pick Number", tick0=1, dtick=1)
    st.plotly_chart(fig_slots, use_container_width=True)

    # ==========================================
    # TEAMS & POSITIONS
    # ==========================================
    st.divider()
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Most Drafted NFL Teams")
        # Ensure all 32 teams could be represented, sorted by count
        team_counts = owner_df['Team'].value_counts().reset_index()
        team_counts.columns = ['NFL Team', 'Count']
        
        fig_teams = px.bar(
            team_counts, 
            y='NFL Team', 
            x='Count', 
            orientation='h',
            height=700,
            color='Count',
            color_continuous_scale='Blues',
            text='Count'
        )
        fig_teams.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_teams, use_container_width=True)

    with right_col:
        st.subheader("Most Drafted Positions")
        pos_counts = owner_df['Position'].value_counts().reset_index()
        pos_counts.columns = ['Position', 'Count']
        
        fig_pos = px.bar(
            pos_counts, 
            x='Position', 
            y='Count',
            color='Position',
            text='Count',
            title="Positional Strategy (All Rounds)"
        )
        st.plotly_chart(fig_pos, use_container_width=True)

    # ==========================================
    # DATA SEARCH
    # ==========================================
    st.divider()
    st.subheader("Raw Draft Data")
    display_df = owner_df[['Year', 'Round', 'Pick', 'Player Name', 'Team', 'Position', 'Age When Drafted']].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
