import streamlit as st
import pandas as pd
import plotly.express as px

# 1. PAGE SETUP
st.set_page_config(page_title="KFL Archive", layout="wide")

# 2. DATA LOADING
@st.cache_data
def load_data():
    # Load both Excel files from your GitHub
    draft_df = pd.read_excel('Draft Data GPT (1).xlsx')
    history_df = pd.read_excel('OFFICIAL Every Game GPT.xlsx', sheet_name='Every Game')
    return draft_df, history_df

# Helper for Name Logic (Handles Jr., III, etc.)
def get_clean_names(name):
    if pd.isna(name): return "", ""
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V', 'JR.', 'SR.']
    parts = str(name).split()
    if len(parts) <= 1: return parts[0] if parts else "", ""
    if parts[-1].upper() in suffixes:
        return " ".join(parts[:-2]), " ".join(parts[-2:])
    return " ".join(parts[:-1]), parts[-1]

try:
    draft_df, history_df = load_data()

    # ==========================================
    # SIDEBAR: KFL BRANDING & NAVIGATION
    # ==========================================
    st.sidebar.markdown("# 🏈 KFL")
    st.sidebar.markdown("### *Kennesaw Football League*")
    st.sidebar.divider()

    # Main Tabs
    main_page = st.sidebar.radio(
        "MAIN MENU",
        ["Draft Room", "Owner Statistics", "League Records"]
    )

    st.sidebar.divider()
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select a Manager", all_owners)
    
    # Filter global data for the selected owner
    owner_draft = draft_df[draft_df['Owner'] == selected_owner]
    owner_history = history_df[history_df['Owner'] == selected_owner]

    # ==========================================
    # PAGE 1: DRAFT ROOM
    # ==========================================
    if main_page == "Draft Room":
        sub_page = st.sidebar.radio(
            "DRAFT SUB-MENU",
            ["Dashboard", "Archetype", "Performance", "Scoring"]
        )
        
        st.title(f"🎯 Draft Room: {sub_page}")
        st.caption(f"Manager: {selected_owner}")

        # --- SUB-TAB 1: DASHBOARD ---
        if sub_page == "Dashboard":
            st.subheader("At a Glance")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg ROI Score", f"{owner_draft['ROI Score'].mean():.1f}")
            
            # Draft Slot Logic (Round 1 only)
            slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots_df[slots_df['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Historical Draft Slot")
            fig_slots.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig_slots, use_container_width=True)

        # --- SUB-TAB 2: ARCHETYPE (Tendencies) ---
        elif sub_page == "Archetype":
            st.subheader("Manager Tendencies & Player Profiles")

            # ROW 1: AGE & NAMES
            col_age, col_first, col_last = st.columns(3)

            # Age Ranking Logic
            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1

            with col_age:
                st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
                with st.popover(f"Rank: {age_rank}/{len(league_age)} vs League"):
                    st.markdown("### League Average Age")
                    age_table = league_age.reset_index()
                    age_table.columns = ['Owner', 'Avg Age']
                    age_table.index += 1
                    st.table(age_table.style.format({'Avg Age': '{:.1f}'}))

            # Refined Name Logic (Filter D/ST and handles suffixes)
            names_df = owner_draft[~owner_draft['Position'].str.upper().isin(['DST', 'DEF', 'D/ST', 'DEFENSE'])].copy()
            names_df = names_df.dropna(subset=['Player Name'])
            names_df[['First', 'Last']] = names_df['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))

            with col_first:
                if not names_df['First'].empty:
                    common_first = names_df['First'].mode()[0]
                    st.metric("Common First Name", common_first)
                    with st.popover("View Full List"):
                        st.write(f"Players named **{common_first}** drafted by {selected_owner}:")
                        st.dataframe(names_df[names_df['First'] == common_first][['Year', 'Player Name', 'Position']].sort_values('Year'), hide_index=True)

            with col_last:
                if not names_df['Last'].empty:
                    common_last = names_df['Last'].mode()[0]
                    st.metric("Common Last Name", common_last)
                    with st.popover("View Full List"):
                        st.write(f"Players with last name **{common_last}** drafted by {selected_owner}:")
                        st.dataframe(names_df[names_df['Last'] == common_last][['Year', 'Player Name', 'Position']].sort_values('Year'), hide_index=True)

            st.divider()

            # ROW 2: TEAM RELIANCE (FIXED VERTICAL CHART)
            st.subheader("NFL Team Reliance")
            st.caption("Which franchises do you trust most? (Includes all 32 teams)")
            all_nfl_teams = sorted(draft_df['Team'].unique())
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl_teams, fill_value=0).reset_index()
            team_counts.columns = ['Team', 'Picks']
            team_counts = team_counts.sort_values('Picks', ascending=False)

            fig_teams = px.bar(
                team_counts, x='Team', y='Picks', text='Picks',
                color='Picks', color_continuous_scale='Blues',
                height=500, title="Career Picks by NFL Franchise"
            )
            fig_teams.update_layout(
                xaxis_tickangle=-45, 
                xaxis_title="NFL Team",
                yaxis_title="Times Drafted",
                margin=dict(b=100),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_teams, use_container_width=True)

            st.divider()

            # ROW 3: FREQUENT FACES & POSITIONS
            col_freq, col_pos = st.columns(2)
            with col_freq:
                st.subheader("Frequent Faces")
                st.caption("Players drafted more than once")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player', 'Drafted']
                st.dataframe(repeats[repeats['Drafted'] >= 2], use_container_width=True, hide_index=True)

            with col_pos:
                st.subheader("Position Breakdown")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                st.plotly_chart(px.pie(pos_counts, values='count', names='Position', hole=0.4), use_container_width=True)

        # --- SUB-TAB 3: PERFORMANCE & 4. SCORING (Placeholders) ---
        elif sub_page == "Performance":
            st.subheader("Value Over ADP (VOADP) Analysis")
            st.plotly_chart(px.scatter(owner_draft, x="Round", y="VOADP", color="VOADP Tier", size="Points", hover_data=["Player Name"]), use_container_width=True)

        elif sub_page == "Scoring":
            st.subheader("Production Metrics")
            st.plotly_chart(px.scatter(owner_draft, x="GP", y="Points", color="Position", size="PPG", hover_data=["Player Name"]), use_container_width=True)

    # ==========================================
    # PAGE 2: OWNER STATISTICS
    # ==========================================
    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Performance")
        
        wins = len(owner_history[owner_history['Result'] == 'Win'])
        losses = len(owner_history[owner_history['Result'] == 'Loss'])
        st.metric("All-Time Record", f"{wins}-{losses}")

        st.subheader("⚔️ Head-to-Head Rivalries")
        opponent = st.selectbox("Compare against:", [o for o in all_owners if o != selected_owner])
        rivalry = owner_history[owner_history['Opponent'] == opponent]
        st.write(f"**Record vs {opponent}:** {len(rivalry[rivalry['Result']=='Win'])}W - {len(rivalry[rivalry['Result']=='Loss'])}L")
        st.dataframe(rivalry[['Year', 'Week', 'Points', 'Points Against', 'Result']], hide_index=True)

    # ==========================================
    # PAGE 3: LEAGUE RECORDS
    # ==========================================
    elif main_page == "League Records":
        st.title("📜 KFL Hall of Records")
        st.subheader("All-Time Single Game Highs")
        st.dataframe(history_df.sort_values('Points', ascending=False).head(10)[['Year', 'Owner', 'Points', 'Opponent']], hide_index=True)

except Exception as e:
    st.error(f"KFL App Error: {e}")
