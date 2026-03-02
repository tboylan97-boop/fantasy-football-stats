import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup
st.set_page_config(page_title="KFL Archive", layout="wide")

# 2. Data Loading
@st.cache_data
def load_data():
    draft_df = pd.read_excel('Draft Data GPT (1).xlsx')
    # Loading 'Every Game' sheet for Owner Statistics
    history_df = pd.read_excel('OFFICIAL Every Game GPT.xlsx', sheet_name='Every Game')
    return draft_df, history_df

try:
    draft_df, history_df = load_data()

    # ==========================================
    # SIDEBAR: KFL BRANDING & NAVIGATION
    # ==========================================
    st.sidebar.markdown("# 🏈 KFL")
    st.sidebar.markdown("### *Kennesaw Football League*")
    st.sidebar.divider()

    # NAVIGATION TABS
    page = st.sidebar.radio(
        "NAVIGATION",
        ["Draft Room", "Owner Statistics", "League Records"]
    )

    st.sidebar.divider()

    # MANAGER SELECTION (Global for all pages)
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select a Manager", all_owners)
    
    # Pre-filtering data for the owner
    owner_draft = draft_df[draft_df['Owner'] == selected_owner]
    owner_history = history_df[history_df['Owner'] == selected_owner]

    # ==========================================
    # PAGE 1: DRAFT ROOM
    # ==========================================
    if page == "Draft Room":
        st.title(f"🎯 Draft Room: {selected_owner}")

        # LOGIC: DRAFT SLOTS (ROUND 1 ONLY)
        slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
        league_avg_slots = slots_df.groupby('Owner')['Pick'].mean().sort_values()
        owner_avg_slot = league_avg_slots[selected_owner]
        pick_rank = league_avg_slots.index.get_loc(selected_owner) + 1

        # League Age Ranking
        league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
        age_rank = league_age.index.get_loc(selected_owner) + 1

        # BIG METRICS
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Drafted Assets", len(owner_draft))
        col2.metric("League Seasons", owner_draft['Year'].nunique())
        
        with col3:
            st.metric("Avg Draft Pick", f"{owner_avg_slot:.1f}")
            with st.popover(f"Rank: {pick_rank}/{len(league_avg_slots)}"):
                rank_table = league_avg_slots.reset_index()
                rank_table.columns = ['Owner', 'Avg Pick']
                rank_table.index += 1
                st.table(rank_table.style.format({'Avg Pick': '{:.1f}'}))

        with col4:
            st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
            with st.popover(f"Rank: {age_rank}/{len(league_age)}"):
                age_table = league_age.reset_index()
                age_table.columns = ['Owner', 'Avg Age']
                age_table.index += 1
                st.table(age_table.style.format({'Avg Age': '{:.1f}'}))

        st.divider()
        
        # VISUALS
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Historical Draft Slot")
            fig_slots = px.bar(slots_df[slots_df['Owner'] == selected_owner], x='Year', y='Pick', text='Pick')
            fig_slots.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_slots, use_container_width=True)
        
        with c2:
            st.subheader("Position Breakdown")
            pos_counts = owner_draft['Position'].value_counts().reset_index()
            fig_pos = px.pie(pos_counts, values='count', names='Position', hole=0.4)
            st.plotly_chart(fig_pos, use_container_width=True)

    # ==========================================
    # PAGE 2: OWNER STATISTICS
    # ==========================================
    elif page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Performance")

        # Win/Loss Logic
        wins = len(owner_history[owner_history['Result'] == 'Win'])
        losses = len(owner_history[owner_history['Result'] == 'Loss'])
        total_games = wins + losses
        win_pct = (wins / total_games) * 100 if total_games > 0 else 0

        # PERFORMANCE METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("All-Time Record", f"{wins}-{losses}")
        m2.metric("Win Percentage", f"{win_pct:.1f}%")
        m3.metric("Total Pts For", f"{owner_history['Points'].sum():,.1f}")
        m4.metric("Avg Pts/Game", f"{owner_history['Points'].mean():.1f}")

        st.divider()

        # RIVALRY SECTION
        st.subheader("⚔️ Rivalry Breakdown")
        opponent = st.selectbox("Select Rival", [o for o in all_owners if o != selected_owner])
        rivalry = owner_history[owner_history['Opponent'] == opponent]
        
        r_wins = len(rivalry[rivalry['Result'] == 'Win'])
        r_losses = len(rivalry[rivalry['Result'] == 'Loss'])
        
        st.write(f"### Record vs {opponent}: {r_wins}W - {r_losses}L")
        st.dataframe(rivalry[['Year', 'Week', 'Points', 'Points Against', 'Result']], use_container_width=True, hide_index=True)

    # ==========================================
    # PAGE 3: LEAGUE RECORDS
    # ==========================================
    elif page == "League Records":
        st.title("📜 KFL Hall of Records")
        
        # All-time single game high
        st.subheader("All-Time Single Game Highs")
        high_scores = history_df.sort_values('Points', ascending=False).head(10)
        st.dataframe(high_scores[['Year', 'Week', 'Owner', 'Points', 'Opponent']], hide_index=True)

        # Season Champions (using the Win Championship column from draft data)
        st.subheader("KFL Champions")
        champs = draft_df[draft_df['Win Championship?'] == 'Yes'][['Year', 'Owner']].drop_duplicates()
        st.table(champs.sort_values('Year', ascending=False))

except Exception as e:
    st.error(f"Error loading KFL data: {e}")
