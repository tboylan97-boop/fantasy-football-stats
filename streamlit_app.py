import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup
st.set_page_config(page_title="The Ultimate Draft Room", layout="wide")

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
    slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
    
    # Calculate league-wide averages for the Rank Popover
    league_avg_slots = slots_df.groupby('Owner')['Pick'].mean().sort_values()
    
    # Selected owner stats
    owner_avg_slot = league_avg_slots[selected_owner]
    pick_rank = league_avg_slots.index.get_loc(selected_owner) + 1

    # League Age Ranking Logic
    league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
    age_rank = league_age.index.get_loc(selected_owner) + 1

    # ==========================================
    # TOP ROW: THE BIG STATS (WITH CLICKABLE POP-UPS)
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
        # Show the 1-12 Average
        st.metric("Average Draft Pick", f"{owner_avg_slot:.1f}")
        
        # --- CLICKABLE RANKING WINDOW ---
        with st.popover(f"🏆 Rank: {pick_rank}/{len(league_avg_slots)}"):
            st.markdown("### Draft Slot Leaderboard")
            st.caption("Sorted by Lowest Average Draft Position (1-12)")
            
            # Formatting the table for the pop-up
            pick_ranking_table = league_avg_slots.reset_index()
            pick_ranking_table.columns = ['Owner', 'Avg Pick']
            pick_ranking_table.index = pick_ranking_table.index + 1 # Start rank at 1
            
            st.table(pick_ranking_table.style.format({'Avg Pick': '{:.1f}'}))

    with col4:
        avg_age = owner_df['Age When Drafted'].mean()
        st.metric("Avg Player Age", f"{avg_age:.1f}")
        
        # --- CLICKABLE AGE RANKING WINDOW ---
        with st.popover(f"🎂 Rank: {age_rank}/{len(league_age)}"):
            st.markdown("### Age Preference Leaderboard")
            st.caption("Sorted from Youngest Average to Oldest")
            
            age_ranking_table = league_age.reset_index()
            age_ranking_table.columns = ['Owner', 'Avg Age']
            age_ranking_table.index = age_ranking_table.index + 1
            
            st.table(age_ranking_table.style.format({'Avg Age': '{:.1f}'}))

    st.divider()

    # ==========================================
    # CHART: DRAFT SLOT HISTORY (ROUND 1 ONLY)
    # ==========================================
    st.subheader("Historical Draft Slot (Round 1)")
    owner_slots = slots_df[slots_df['Owner'] == selected_owner].sort_values('Year')
    
    fig_slots = px.bar(
        owner_slots, 
        x='Year', 
        y='Pick', 
        text='Pick',
        title="Round 1 Pick History",
        color_discrete_sequence=['#3b82f6']
    )
    # Reverse Y-axis so Pick 1 is at the top
    fig_slots.update_yaxes(autorange="reversed", title="Pick Number", tick0=1, dtick=1)
    st.plotly_chart(fig_slots, use_container_width=True)

    # ==========================================
    # TEAMS & POSITIONS
    # ==========================================
    st.divider()
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Most Drafted NFL Teams")
        team_counts = owner_df['Team'].value_counts().reset_index()
        team_counts.columns = ['NFL Team', 'Count']
        
        fig_teams = px.bar(
            team_counts, 
            y='NFL Team', 
            x='Count', 
            orientation='h',
            height=700, # Tall enough to see all teams
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
            title="Positional Breakdown (Career)"
        )
        st.plotly_chart(fig_pos, use_container_width=True)

    # ==========================================
    # DATA SEARCH
    # ==========================================
    st.divider()
    st.subheader("Raw Draft Data")
    # Simplify view for the final table
    final_table_df = owner_df[['Year', 'Round', 'Pick', 'Player Name', 'Team', 'Position', 'Age When Drafted']].copy()
    st.dataframe(final_table_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Something went wrong: {e}")
    st.info("Check that 'Draft Data GPT (1).xlsx' is uploaded to your GitHub repository.")
