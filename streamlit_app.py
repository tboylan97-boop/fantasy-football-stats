import streamlit as st
import pandas as pd
import plotly.express as px

# 1. PAGE SETUP
st.set_page_config(page_title="KFL Archive", layout="wide")

# 2. DATA LOADING & CLEANING
@st.cache_data
def load_data():
    draft_df = pd.read_excel('Draft Data GPT (1).xlsx')
    history_df = pd.read_excel('OFFICIAL Every Game GPT.xlsx', sheet_name='Every Game')
    
    # Standardize data to prevent duplicates
    draft_df['Team'] = draft_df['Team'].astype(str).str.strip().str.upper()
    draft_df['Owner'] = draft_df['Owner'].astype(str).str.strip()
    draft_df['Position'] = draft_df['Position'].astype(str).str.strip().str.upper()
    
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

    # --- SIDEBAR & NAV ---
    st.sidebar.markdown("# 🏈 KFL")
    st.sidebar.markdown("### *Kennesaw Football League*")
    st.sidebar.divider()
    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])
    st.sidebar.divider()
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner]
    owner_history = history_df[history_df['Owner'] == selected_owner]

    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        st.title(f"🎯 {selected_owner}: {sub_page}")

        if sub_page == "Dashboard":
            st.subheader("At a Glance")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg ROI Score", f"{owner_draft['ROI Score'].mean():.1f}")
            
            slots = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots[slots['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Round 1 Slot History")
            fig_slots.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig_slots, use_container_width=True)

        elif sub_page == "Archetype":
            # --- SECTION 1: AGE & NAMES ---
            st.subheader("Manager Tendencies")
            col_age, col_first, col_last = st.columns(3)
            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1

            with col_age:
                st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
                with st.popover(f"Rank: {age_rank}/{len(league_age)}"):
                    st.table(league_age.reset_index().rename(columns={'index':'Owner','Age When Drafted':'Age'}))

            names_df = owner_draft[~owner_draft['Position'].isin(['DST', 'DEF', 'D/ST'])].copy()
            names_df[['First', 'Last']] = names_df['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))

            with col_first:
                cf = names_df['First'].mode()[0] if not names_df['First'].empty else "N/A"
                st.metric("Common First Name", cf)
                with st.popover("View Players"):
                    st.dataframe(names_df[names_df['First'] == cf][['Year', 'Player Name', 'Position']], hide_index=True)

            with col_last:
                cl = names_df['Last'].mode()[0] if not names_df['Last'].empty else "N/A"
                st.metric("Common Last Name", cl)
                with st.popover("View Players"):
                    st.dataframe(names_df[names_df['Last'] == cl][['Year', 'Player Name', 'Position']], hide_index=True)

            st.divider()

            # --- SECTION 2: NFL TEAM RELIANCE ---
            st.subheader("NFL Team Reliance")
            all_nfl = sorted(draft_df['Team'].unique())
            team_data = owner_draft['Team'].value_counts().reindex(all_nfl, fill_value=0).reset_index()
            team_data.columns = ['Team', 'Picks']
            team_data = team_data.sort_values('Picks', ascending=False)

            fig_teams = px.bar(team_data, x='Team', y='Picks', text='Picks', color='Picks', color_continuous_scale='Blues', height=450)
            fig_teams.update_layout(xaxis_tickangle=-45, margin=dict(b=100), coloraxis_showscale=False)
            st.plotly_chart(fig_teams, use_container_width=True)

            # Team Drill-down
            active_teams = sorted(owner_draft[owner_draft['Team'] != 'N/A']['Team'].unique())
            sel_team = st.selectbox("View history with the:", active_teams)
            with st.popover(f"📋 View all {sel_team} Picks"):
                team_hist = owner_draft[owner_draft['Team'] == sel_team][['Year', 'Round', 'Pick', 'Player Name', 'Position', 'ROI Score']].sort_values('Year', ascending=False)
                st.dataframe(team_hist, hide_index=True, use_container_width=True)

            st.divider()

            # --- SECTION 3: ROUND BY ROUND ANALYSIS ---
            st.subheader("Round-by-Round Breakdown")
            available_rounds = sorted(owner_draft['Round'].unique())
            selected_round = st.select_slider("Slide to Toggle Round", options=available_rounds)
            round_df = owner_draft[owner_draft['Round'] == selected_round]
            
            r_col1, r_col2 = st.columns([1, 2])
            with r_col1:
                st.metric("Picks Made", len(round_df))
                st.metric("Avg PPG", f"{round_df['PPG'].mean():.1f}")
            with r_col2:
                st.dataframe(round_df[['Year', 'Pick', 'Player Name', 'Position', 'Team']], hide_index=True, use_container_width=True)

            st.divider()

            # --- SECTION 4: DEMOGRAPHICS (Birth Month & Race) ---
            st.subheader("Player Demographics")
            demo_left, demo_right = st.columns(2)

            with demo_left:
                st.write("#### 🎂 Birth Month Frequency")
                # Grouping by month
                month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                               'July', 'August', 'September', 'October', 'November', 'December']
                month_counts = owner_draft['Birth Month'].value_counts().reindex(month_order, fill_value=0).reset_index()
                month_counts.columns = ['Month', 'Picks']
                
                fig_month = px.bar(month_counts, x='Picks', y='Month', orientation='h', 
                                   color='Picks', color_continuous_scale='Sunset')
                fig_month.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig_month, use_container_width=True)

                # Month Drill-down
                sel_month = st.selectbox("View players born in:", month_order)
                with st.popover(f"🎈 View {sel_month} Birthdays"):
                    m_df = owner_draft[owner_draft['Birth Month'] == sel_month][['Year', 'Player Name', 'Position', 'Team']]
                    st.dataframe(m_df.sort_values('Year', ascending=False), hide_index=True)

            with demo_right:
                st.write("#### 🧬 Racial Breakdown")
                race_counts = owner_draft['Race'].value_counts().reset_index()
                race_counts.columns = ['Race', 'Count']
                
                fig_race = px.pie(race_counts, values='Count', names='Race', hole=0.5)
                fig_race.update_traces(textinfo='percent+label', textfont_size=14)
                st.plotly_chart(fig_race, use_container_width=True)

                # Race Drill-down
                sel_race = st.selectbox("View players by race:", sorted(owner_draft['Race'].unique()))
                with st.popover(f"🧬 View {sel_race} Players"):
                    r_df = owner_draft[owner_draft['Race'] == sel_race][['Year', 'Player Name', 'Position', 'Team']]
                    st.dataframe(r_df.sort_values('Year', ascending=False), hide_index=True)

            st.divider()

            # --- SECTION 5: REPEATS & POSITIONS ---
            col_freq, col_pos = st.columns(2)
            with col_freq:
                st.subheader("Frequent Faces")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player', 'Drafted']
                st.dataframe(repeats[repeats['Drafted'] >= 2], use_container_width=True, hide_index=True)

            with col_pos:
                st.subheader("Position Breakdown")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                pos_counts.columns = ['Position', 'Count']
                fig_pos = px.pie(pos_counts, values='Count', names='Position', hole=0.5)
                fig_pos.update_traces(textinfo='percent+label', textfont_size=14)
                st.plotly_chart(fig_pos, use_container_width=True)

                # Position Drill-down
                sel_pos = st.selectbox("View details for:", sorted(owner_draft['Position'].unique()))
                with st.popover(f"🚀 View all {sel_pos}s"):
                    pos_hist = owner_draft[owner_draft['Position'] == sel_pos][['Year', 'Round', 'Pick', 'Player Name', 'Team']]
                    st.dataframe(pos_hist.sort_values('Year', ascending=False), hide_index=True, use_container_width=True)

        elif sub_page == "Performance":
            st.subheader("VOADP Value Analysis")
            st.plotly_chart(px.scatter(owner_draft, x="Round", y="VOADP", color="VOADP Tier"), use_container_width=True)

        elif sub_page == "Scoring":
            st.subheader("Production Metrics")
            st.plotly_chart(px.scatter(owner_draft, x="GP", y="Points", color="Position", size="PPG"), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
