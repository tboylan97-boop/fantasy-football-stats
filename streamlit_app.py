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
    
    # Standardize column names (remove hidden spaces)
    draft_df.columns = draft_df.columns.str.strip()
    
    # Clean Team & Owner names
    draft_df['Team'] = draft_df['Team'].astype(str).str.strip().str.upper()
    draft_df['Owner'] = draft_df['Owner'].astype(str).str.strip()
    draft_df['Position'] = draft_df['Position'].astype(str).str.strip().str.upper()
    
    return draft_df, history_df

# Helper for Name Logic
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

    # ==========================================
    # PAGE 1: DRAFT ROOM
    # ==========================================
    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("DRAFT SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        st.title(f"🎯 {selected_owner}: {sub_page}")

        if sub_page == "Archetype":
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
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl, fill_value=0).reset_index()
            team_counts.columns = ['Team', 'Picks']
            team_counts = team_counts.sort_values('Picks', ascending=False)
            st.plotly_chart(px.bar(team_counts, x='Team', y='Picks', text='Picks', color='Picks', color_continuous_scale='Blues', height=400), use_container_width=True)

            # Team Drill-down
            active_teams = sorted(owner_draft[owner_draft['Team'] != 'N/A']['Team'].unique())
            sel_team = st.selectbox("View history with the:", active_teams)
            with st.popover(f"📋 View all {sel_team} Picks"):
                team_hist = owner_draft[owner_draft['Team'] == sel_team][['Year', 'Round', 'Pick', 'Player Name', 'Position']].sort_values('Year', ascending=False)
                st.dataframe(team_hist, hide_index=True, use_container_width=True)

            st.divider()

            # --- SECTION 3: ROUND BY ROUND ---
            st.subheader("Round-by-Round Breakdown")
            available_rounds = sorted(owner_draft['Round'].unique())
            selected_round = st.select_slider("Slide to Toggle Round", options=available_rounds)
            round_df = owner_draft[owner_draft['Round'] == selected_round]
            r_c1, r_c2 = st.columns([1, 2])
            r_c1.metric("Picks Made", len(round_df))
            r_c1.metric("Avg PPG", f"{round_df['PPG'].mean():.1f}")
            r_c2.dataframe(round_df[['Year', 'Pick', 'Player Name', 'Position', 'Team']], hide_index=True, use_container_width=True)

            st.divider()

            # --- SECTION 4: DEMOGRAPHICS (Birth Month & Race) ---
            st.subheader("Player Demographics")
            demo_left, demo_right = st.columns(2)

            # --- BIRTH MONTH LOGIC (Failsafe) ---
            month_col = next((c for c in owner_draft.columns if 'Birth' in c or 'Month' in c), None)
            
            with demo_left:
                st.write("#### 🎂 Birth Month Frequency")
                if month_col:
                    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                    month_counts = owner_draft[month_col].value_counts().reindex(months, fill_value=0).reset_index()
                    month_counts.columns = ['Month', 'Picks']
                    st.plotly_chart(px.bar(month_counts, x='Picks', y='Month', orientation='h', color='Picks', color_continuous_scale='Sunset', height=400), use_container_width=True)
                    
                    sel_month = st.selectbox("View players born in:", months)
                    with st.popover(f"🎈 View {sel_month} Birthdays"):
                        m_df = owner_draft[owner_draft[month_col] == sel_month][['Year', 'Player Name', 'Position', 'Team']]
                        st.dataframe(m_df.sort_values('Year', ascending=False), hide_index=True)
                else:
                    st.warning("Could not find 'Birth Month' column in Excel. Please check column name.")

            # --- RACE LOGIC ---
            with demo_right:
                st.write("#### 🧬 Racial Breakdown")
                if 'Race' in owner_draft.columns:
                    race_counts = owner_draft['Race'].value_counts().reset_index()
                    race_counts.columns = ['Race', 'Count']
                    st.plotly_chart(px.pie(race_counts, values='Count', names='Race', hole=0.5), use_container_width=True)
                    
                    sel_race = st.selectbox("View players by race:", sorted(owner_draft['Race'].unique()))
                    with st.popover(f"🧬 View {sel_race} Players"):
                        r_df = owner_draft[owner_draft['Race'] == sel_race][['Year', 'Player Name', 'Position', 'Team']]
                        st.dataframe(r_df.sort_values('Year', ascending=False), hide_index=True)
                else:
                    st.warning("Could not find 'Race' column in Excel.")

            st.divider()

            # --- SECTION 5: REPEATS & POSITION BREAKDOWN ---
            st.subheader("Frequent Faces & Final Tally")
            col_freq, col_pos = st.columns(2)
            
            with col_freq:
                st.write("#### Frequent Faces")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player', 'Drafted']
                st.dataframe(repeats[repeats['Drafted'] >= 2], use_container_width=True, hide_index=True)

            with col_pos:
                st.write("#### Position Strategy")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                pos_counts.columns = ['Position', 'Count']
                fig_pos = px.pie(pos_counts, values='Count', names='Position', hole=0.4)
                fig_pos.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pos, use_container_width=True)

        # Performance and Scoring Placeholders
        elif sub_page == "Performance":
            st.subheader("Performance Analysis Coming Soon")
        elif sub_page == "Scoring":
            st.subheader("Scoring Analysis Coming Soon")

except Exception as e:
    st.error(f"Sync failed: {e}")
