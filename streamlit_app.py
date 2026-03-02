import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup
st.set_page_config(page_title="KFL Archive", layout="wide")

# 2. Data Loading
@st.cache_data
def load_data():
    # Load both Excel files
    draft_df = pd.read_excel('Draft Data GPT (1).xlsx')
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

    main_page = st.sidebar.radio(
        "MAIN MENU",
        ["Draft Room", "Owner Statistics", "League Records"]
    )

    st.sidebar.divider()
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select a Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner]

    # ==========================================
    # DRAFT ROOM: SUB-CATEGORY LOGIC
    # ==========================================
    if main_page == "Draft Room":
        sub_page = st.sidebar.radio(
            "DRAFT SUB-MENU",
            ["Dashboard", "Archetype", "Performance", "Scoring"]
        )
        
        st.title(f"🎯 Draft Room: {sub_page}")
        st.caption(f"Manager: {selected_owner}")

        # --- 1. DASHBOARD ---
        if sub_page == "Dashboard":
            st.subheader("At a Glance")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg ROI Score", f"{owner_draft['ROI Score'].mean():.1f}")
            
            slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots_df[slots_df['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Historical Draft Slot")
            fig_slots.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_slots, use_container_width=True)

        # --- 2. ARCHETYPE (Tendencies) ---
        elif sub_page == "Archetype":
            st.subheader("Manager Tendencies & Player Profiles")

            # --- ROW 1: AGE & NAME POP-UPS ---
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

            # NAME ANALYSIS (Filter out D/ST)
            names_df = owner_draft[~owner_draft['Position'].str.upper().isin(['DST', 'DEF', 'D/ST', 'DEFENSE'])].copy()
            names_df = names_df.dropna(subset=['Player Name'])
            names_df['First'] = names_df['Player Name'].apply(lambda x: x.split()[0] if len(x.split()) > 0 else "")
            names_df['Last'] = names_df['Player Name'].apply(lambda x: x.split()[-1] if len(x.split()) > 1 else "")

            with col_first:
                if not names_df['First'].empty:
                    common_first = names_df['First'].mode()[0]
                    st.metric("Common First Name", common_first)
                    with st.popover("View Full List"):
                        st.write(f"Players named **{common_first}** drafted by {selected_owner}:")
                        st.dataframe(names_df[names_df['First'] == common_first][['Year', 'Player Name']].drop_duplicates(), hide_index=True)
                else:
                    st.metric("Common First Name", "N/A")

            with col_last:
                if not names_df['Last'].empty:
                    common_last = names_df['Last'].mode()[0]
                    st.metric("Common Last Name", common_last)
                    with st.popover("View Full List"):
                        st.write(f"Players with last name **{common_last}** drafted by {selected_owner}:")
                        st.dataframe(names_df[names_df['Last'] == common_last][['Year', 'Player Name']].drop_duplicates(), hide_index=True)
                else:
                    st.metric("Common Last Name", "N/A")

            st.divider()

            # --- ROW 2: TEAM RELIANCE (Full 32 Teams) ---
            st.subheader("NFL Team Reliance (Full Career History)")
            all_nfl_teams = sorted(draft_df['Team'].unique())
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl_teams, fill_value=0).reset_index()
            team_counts.columns = ['NFL Team', 'Picks']
            team_counts = team_counts.sort_values('Picks', ascending=True)

            fig_teams = px.bar(team_counts, x='Picks', y='NFL Team', orientation='h', height=800, text='Picks', color='Picks', color_continuous_scale='Blues')
            st.plotly_chart(fig_teams, use_container_width=True)

            st.divider()

            # --- ROW 3: FREQUENT FACES & POSITIONS ---
            col_freq, col_pos = st.columns(2)
            with col_freq:
                st.subheader("Frequent Faces")
                st.caption("Players drafted by this owner more than once")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player Name', 'Times Drafted']
                repeats = repeats[repeats['Times Drafted'] >= 2]
                if not repeats.empty:
                    st.dataframe(repeats, use_container_width=True, hide_index=True)
                else:
                    st.write("No repeats found for this manager.")

            with col_pos:
                st.subheader("Position Breakdown")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                st.plotly_chart(px.pie(pos_counts, values='count', names='Position', hole=0.4), use_container_width=True)

        # --- 3. PERFORMANCE (Value) ---
        elif sub_page == "Performance":
            st.subheader("Draft Value & ROI Analysis")
            fig_roi = px.scatter(owner_draft, x="Round", y="VOADP", color="VOADP Tier", size="Points", hover_data=["Player Name", "Year"])
            st.plotly_chart(fig_roi, use_container_width=True)

        # --- 4. SCORING (Output) ---
        elif sub_page == "Scoring":
            st.subheader("Production & Reliability")
            sc1, sc2 = st.columns(2)
            sc1.metric("Avg PPG", f"{owner_draft['PPG'].mean():.1f}")
            sc2.metric("Total Games Missed", f"{owner_draft['Games missed'].sum():.0f}")
            st.plotly_chart(px.scatter(owner_draft, x="GP", y="Points", color="Position", size="PPG"), use_container_width=True)

    # ==========================================
    # OTHER PAGES (OWNER STATS & RECORDS)
    # ==========================================
    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Performance")
        wins = len(history_df[(history_df['Owner'] == selected_owner) & (history_df['Result'] == 'Win')])
        losses = len(history_df[(history_df['Owner'] == selected_owner) & (history_df['Result'] == 'Loss')])
        st.metric("All-Time Record", f"{wins}-{losses}")
        
    elif main_page == "League Records":
        st.title("📜 KFL Hall of Records")
        st.subheader("All-Time Single Game Highs")
        st.dataframe(history_df.sort_values('Points', ascending=False).head(10)[['Year', 'Week', 'Owner', 'Points']], hide_index=True)

except Exception as e:
    st.error(f"Error loading KFL data: {e}")
