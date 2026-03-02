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

        # 1. PRE-CALCULATE LEAGUE WIDE STATS FOR RANKINGS
        # ----------------------------------------------
        # Average Age per Owner
        league_age = df.groupby('Owner')['Age When Drafted'].mean().sort_values()
        # Average Draft Slot (Their Pick in Round 1)
        slots = df[df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
        league_slots = slots.groupby('Owner')['Pick'].mean().sort_values()

        # 2. FILTER DATA FOR SELECTED OWNER
        # ----------------------------------------------
        owner_df = df[df['Owner'] == selected_owner]
        owner_slots = slots[slots['Owner'] == selected_owner]

        # 3. TOP ROW: KEY METRICS
        # ----------------------------------------------
        st.subheader("The Resume")
        k1, k2, k3, k4 = st.columns(4)
        
        # Total Drafts (Unique Years)
        num_drafts = owner_df['Year'].nunique()
        k1.metric("Total Drafts", f"{num_drafts}")
        
        # Total Picks
        k2.metric("Total Picks", f"{len(owner_df)}")

        # Avg Draft Slot & Rank
        avg_slot = owner_slots['Pick'].mean()
        slot_rank = league_slots.index.get_loc(selected_owner) + 1
        k3.metric("Avg Draft Slot", f"{avg_slot:.1f}", f"Rank: {slot_rank}/{len(league_slots)}")

        # Avg Age & Rank
        avg_age = owner_df['Age When Drafted'].mean()
        age_rank = league_age.index.get_loc(selected_owner) + 1
        k4.metric("Avg Player Age", f"{avg_age:.1f}", f"Rank: {age_rank}/{len(league_age)}")

        # 4. DRAFT SLOT HISTORY CHART
        # ----------------------------------------------
        st.divider()
        st.subheader("Draft Slot History")
        st.info("Which pick did you have in Round 1 each year?")
        fig_slots = px.bar(owner_slots, x='Year', y='Pick', 
                           title=f"Draft Slot by Year",
                           labels={'Pick': 'Pick Number (Round 1)'},
                           color_discrete_sequence=['#94a3b8'])
        # Invert Y axis because Pick 1 is "Higher" than Pick 12
        fig_slots.update_yaxes(autorange="reversed") 
        st.plotly_chart(fig_slots, use_container_width=True)

        # 5. TEAMS & POSITIONS
        # ----------------------------------------------
        col_team, col_pos = st.columns(2)

        with col_team:
            st.subheader("Most Drafted NFL Teams")
            team_counts = owner_df['Team'].value_counts().reset_index()
            team_counts.columns = ['NFL Team', 'Count']
            fig_teams = px.bar(team_counts, x='Count', y='NFL Team', 
                               orientation='h', 
                               title="Picks by NFL Team",
                               height=600)
            fig_teams.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_teams, use_container_width=True)

        with col_pos:
            st.subheader("Most Drafted Positions")
            pos_counts = owner_df['Position'].value_counts().reset_index()
            pos_counts.columns = ['Position', 'Count']
            fig_pos = px.pie(pos_counts, values='Count', names='Position', 
                             title="Positional Breakdown",
                             hole=0.4)
            st.plotly_chart(fig_pos, use_container_width=True)

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
