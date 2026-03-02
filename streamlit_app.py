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
    draft_df.columns = draft_df.columns.str.strip()
    
    # Smart Birthday Converter
    if 'Birthday' in draft_df.columns:
        draft_df['Birthday'] = pd.to_datetime(draft_df['Birthday'], errors='coerce')
        draft_df['Birth Month'] = draft_df['Birthday'].dt.month_name()
    
    # Fill empty cells
    for col in ['Birth Month', 'Race', 'VOADP Tier']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].fillna('Unknown').astype(str)

    # Standardize Team, Owner, and Position
    for col in ['Team', 'Owner', 'Position']:
        draft_df[col] = draft_df[col].astype(str).str.strip().str.upper()
    
    # CRITICAL FIX: Ensure PPG and Success Metrics are numbers and never negative
    for col in ['PPG', 'GP', 'VOADP', 'Points', '% of PIP']:
        if col in draft_df.columns:
            draft_df[col] = pd.to_numeric(draft_df[col], errors='coerce').fillna(0)
    
    return draft_df, history_df

# 3. ADVANCED ANALYTICS FORMULAS
def calculate_success_score(row):
    # 60% Season Production (PPG * GP) - Base target 210 total pts
    ppg = max(0, row.get('PPG', 0))
    gp = max(0, row.get('GP', 0))
    reg_score = min(60, ((ppg * gp) / 210) * 60)
    
    # 25% Draft Value (VOADP) - Target 50+ movement
    voadp = max(0, row.get('VOADP', 0))
    roi_score = min(25, (voadp / 50) * 25)
    
    # 15% Postseason Impact (% of PIP) - Target 20%
    pip = max(0, row.get('% of PIP', 0))
    clutch_score = min(15, (pip / 0.20) * 15)
    
    return round(reg_score + roi_score + clutch_score, 1)

def get_grade(score):
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"

# Helper for Name Logic
def get_clean_names(name):
    if pd.isna(name): return "", ""
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V', 'JR.', 'SR.']
    parts = str(name).split()
    if len(parts) <= 1: return parts[0] if parts else "", ""
    if parts[-1].upper() in suffixes:
        return " ".join(parts[:-2]), " ".join(parts[:-2:])
    return " ".join(parts[:-1]), parts[-1]

try:
    draft_df, history_df = load_data()
    all_owners = sorted(draft_df['Owner'].unique())
    
    # SIDEBAR
    st.sidebar.markdown("# 🏈 KFL")
    st.sidebar.markdown("### *Kennesaw Football League*")
    st.sidebar.divider()
    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])
    st.sidebar.divider()
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner].copy()
    owner_history = history_df[history_df['Owner'] == selected_owner]
    
    # Apply Success Score
    owner_draft['Success Score'] = owner_draft.apply(calculate_success_score, axis=1)
    owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)

    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
        # --- DASHBOARD ---
        if sub_page == "Dashboard":
            st.title(f"📈 {selected_owner}: Dashboard")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Career Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg Success Score", f"{owner_draft['Success Score'].mean():.1f}")
            
            slots = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots[slots['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Round 1 Draft Slot History")
            fig_slots.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig_slots, use_container_width=True)

        # --- ARCHETYPE ---
        elif sub_page == "Archetype":
            st.title(f"🧬 {selected_owner}: Draft Archetype")
            
            col_age, col_first, col_last = st.columns(3)
            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1
            with col_age:
                st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
                with st.popover(f"Rank: {age_rank}/{len(league_age)}"):
                    st.table(league_age.reset_index().rename(columns={'index':'Owner','Age When Drafted':'Age'}))

            valid_players = owner_draft[~owner_draft['Position'].isin(['DST', 'DEF', 'D/ST', 'DEFENSE'])].copy()
            valid_players[['First', 'Last']] = valid_players['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))
            
            with col_first:
                cf = valid_players['First'].mode()[0] if not valid_players['First'].empty else "N/A"
                st.metric("Common First Name", cf)
            with col_last:
                cl = valid_players['Last'].mode()[0] if not valid_players['Last'].empty else "N/A"
                st.metric("Common Last Name", cl)

            st.divider()
            st.subheader("NFL Team Reliance")
            all_nfl = sorted(draft_df['Team'].unique())
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl, fill_value=0).reset_index()
            team_counts.columns = ['Team', 'Picks']
            st.plotly_chart(px.bar(team_counts.sort_values('Picks', ascending=False), x='Team', y='Picks', text='Picks', color='Picks', color_continuous_scale='Blues', height=400), use_container_width=True)

            st.divider()
            st.subheader("Round-by-Round Breakdown")
            available_rounds = sorted(owner_draft['Round'].unique())
            selected_round = st.select_slider("Slide to Toggle Round", options=available_rounds)
            round_df = owner_draft[owner_draft['Round'] == selected_round]
            r_c1, r_c2 = st.columns([1, 2])
            r_c1.metric("Picks Made", len(round_df))
            r_c1.metric("Avg PPG", f"{round_df['PPG'].mean():.1f}")
            r_c2.dataframe(round_df[['Year', 'Pick', 'Player Name', 'Position', 'Team']], hide_index=True, use_container_width=True)

            st.divider()
            demo_left, demo_right = st.columns(2)
            with demo_left:
                st.write("#### 🎂 Birth Month Frequency")
                if 'Birth Month' in valid_players.columns:
                    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                    m_counts = valid_players['Birth Month'].value_counts().reindex(months, fill_value=0).reset_index()
                    st.plotly_chart(px.bar(m_counts, x='count', y='Month', orientation='h', color_continuous_scale='Sunset'), use_container_width=True)
            with demo_right:
                st.write("#### 🧬 Racial Breakdown")
                if 'Race' in valid_players.columns:
                    race_counts = valid_players['Race'].value_counts().reset_index()
                    st.plotly_chart(px.pie(race_counts, values='count', names='Race', hole=0.5), use_container_width=True)

        # --- PERFORMANCE (The Report Card) ---
        elif sub_page == "Performance":
            st.title(f"🏆 {selected_owner}: Performance")
            
            # Hall of Fame / Hall of Shame
            hof, hos = st.columns(2)
            with hof:
                st.success("### ⭐ Draft Hall of Fame")
                top_picks = owner_draft.sort_values('Success Score', ascending=False).head(5)
                for _, p in top_picks.iterrows():
                    st.write(f"**{p['Player Name']} ({p['Year']})** - {p['Grade']} ({p['Success Score']})")
            
            with hos:
                st.error("### 🗑️ Draft Hall of Shame")
                real_busts = owner_draft[owner_draft['GP'] > 0].sort_values('Success Score', ascending=True).head(5)
                for _, p in real_busts.iterrows():
                    st.write(f"**{p['Player Name']} ({p['Year']})** - {p['Grade']} ({p['Success Score']})")

            st.divider()
            
            # Scatter Plot
            st.subheader("Success Score by Round")
            owner_draft['bubble_size'] = owner_draft['PPG'].apply(lambda x: max(2, x))
            fig_perf = px.scatter(
                owner_draft, x="Round", y="Success Score", color="Grade", 
                size="bubble_size", hover_data=["Player Name", "Year", "Points"],
                color_discrete_map={"A+":"#00FF00", "A":"#7FFF00", "B":"#FFFF00", "C":"#FFA500", "D":"#FF4500", "F":"#FF0000"}
            )
            st.plotly_chart(fig_perf, use_container_width=True)

            # --- DETAILED REVIEW TABLE (With Column Resizing) ---
            st.subheader("📋 Comprehensive Performance Log")
            st.caption("Review raw stats to refine Success Score logic.")
            
            # Sorting by Success Score to help you see the "A+" picks first
            review_df = owner_draft[[
                'Year', 'Round', 'Pick', 'Player Name', 'Position', 
                'Points', 'PPG', 'GP', 'Success Score', 'Grade'
            ]].sort_values('Success Score', ascending=False)

            st.dataframe(
                review_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Year": st.column_config.NumberColumn("Year", format="%d", width="small"),
                    "Round": st.column_config.NumberColumn("Rd", width="small"),
                    "Pick": st.column_config.NumberColumn("Pk", width="small"),
                    "Player Name": st.column_config.TextColumn("Player", width="medium"),
                    "Position": st.column_config.TextColumn("Pos", width="small"),
                    "Points": st.column_config.NumberColumn("Total Pts", format="%.1f"),
                    "PPG": st.column_config.NumberColumn("PPG", format="%.1f"),
                    "GP": st.column_config.NumberColumn("GP"),
                    "Success Score": st.column_config.ProgressColumn(
                        "Score", help="Ultimate Success Formula", min_value=0, max_value=100, format="%.1f"
                    ),
                    "Grade": st.column_config.TextColumn("Grade", width="small")
                }
            )

    # PAGE 2: OWNER STATISTICS
    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Stats")
        wins = len(owner_history[owner_history['Result'] == 'Win'])
        losses = len(owner_history[owner_history['Result'] == 'Loss'])
        st.metric("All-Time Record", f"{wins}-{losses}")

except Exception as e:
    st.error(f"Sync failed: {e}")
