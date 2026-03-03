import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. PAGE SETUP
st.set_page_config(page_title="KFL Archive", layout="wide")

# 2. DATA LOADING & CLEANING
@st.cache_data
def load_data():
    # Use the specific file name provided in the sidebar/upload
    draft_df = pd.read_csv('Draft Data GPT (1).csv')
    # history_df = pd.read_csv('OFFICIAL Every Game GPT.csv') # Assuming same naming convention
    # For stability in this snippet, I will focus on the draft_df logic provided.
    # Note: If the user has history_df, ensure the file is present.
    try:
        history_df = pd.read_excel('OFFICIAL Every Game GPT.xlsx', sheet_name='Every Game')
    except:
        history_df = pd.DataFrame(columns=['Owner', 'Result']) # Fallback

    draft_df.columns = draft_df.columns.str.strip()
    
    # Clean % columns and numeric columns
    def clean_pct_column(val):
        if pd.isna(val) or val == '#DIV/0!': return 0.0
        val = str(val).replace('%', '').strip()
        try: return float(val) / 100.0
        except: return 0.0

    if '% of PIP' in draft_df.columns:
        draft_df['% of PIP'] = draft_df['% of PIP'].apply(clean_pct_column)

    # Demographic Cleaning
    if 'Birthday' in draft_df.columns:
        draft_df['Birthday'] = pd.to_datetime(draft_df['Birthday'], errors='coerce')
        draft_df['Birth Month'] = draft_df['Birthday'].dt.month_name()
    
    for col in ['Birth Month', 'Race', 'VOADP Tier']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].astype(str).str.strip().replace(['nan', 'None', 'null'], 'Unknown')

    for col in ['Team', 'Owner', 'Position']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].astype(str).str.strip().str.upper()

    for col in ['PPG', 'GP', 'VOADP', 'Points', 'Championship points']:
        if col in draft_df.columns:
            draft_df[col] = pd.to_numeric(draft_df[col], errors='coerce').fillna(0)
    
    return draft_df, history_df

# 3. HELPER FUNCTIONS
def get_grade(score):
    if score >= 98: return "S" 
    if score >= 90: return "A+"
    if score >= 85: return "A"
    if score >= 75: return "B"
    if score >= 65: return "C"
    if score >= 55: return "D"
    if score >= 11: return "F"
    return "F-"

def get_clean_names(name):
    if pd.isna(name): return "", ""
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V', 'JR.', 'SR.']
    parts = str(name).split()
    if len(parts) <= 1: return parts[0] if parts else "", ""
    if parts[-1].upper() in suffixes:
        return " ".join(parts[:-2]), " ".join(parts[:-2:])
    return " ".join(parts[:-1]), parts[-1]

# 4. PERFORMANCE REFINEMENT FORMULA (v3.1)
def refine_score(row, full_data):
    pos = row.get('Position', 'RB')
    pts = row.get('Points', 0)
    ppg = row.get('PPG', 0)
    voadp = row.get('VOADP', 0)
    pip_val = row.get('% of PIP', 0)
    rd = row.get('Round', 1)
    won_champ = str(row.get('Win Championship?', '')).strip().upper() in ['YES', '1', '1.0', 'Y']

    # B1: Absolute Production (40% - vs All-Time Baseline)
    if pos == 'QB': baseline = 330
    elif pos in ['K', 'DST', 'DEF', 'D/ST']: baseline = 215
    elif pos == 'TE': baseline = 175
    else: baseline = 225
    abs_score = min(40, (pts / baseline) * 40)

    # B2: Yearly Dominance (20% - vs Position Top Scorer that year)
    yearly_pos_data = full_data[(full_data['Year'] == row['Year']) & (full_data['Position'] == pos)]
    yearly_max = yearly_pos_data['Points'].max() if not yearly_pos_data.empty else 0
    rel_score = (pts / yearly_max) * 20 if yearly_max > 0 else (pts / baseline) * 20
    
    # B3: Maintenance vs ROI (25%)
    # QBs are anchors in Rds 1-6. Others in Rds 1-2.
    is_high_expectation = (pos == 'QB' and rd <= 6) or (pos in ['RB', 'WR', 'TE'] and rd <= 2)
    
    if is_high_expectation:
        target_ppg = 22 if pos == 'QB' else 19
        val_score = min(25, (ppg / target_ppg) * 25)
    else:
        multiplier = 1.3 if pos in ['RB', 'WR', 'TE'] else 1.0
        val_score = min(25, (max(0, voadp) / 65) * 25 * multiplier)

    # B4: Clutch (15%)
    clutch_score = min(15, (pip_val / 0.22) * 15)
    
    total = abs_score + rel_score + val_score + clutch_score
    if pts > 400: total += 10 
    
    if pos in ['K', 'DST', 'DEF', 'D/ST'] and not won_champ: total = min(79, total)

    if not won_champ: total = min(99.9, total)
    else:
        if total >= 94: total = 100
        elif total >= 80: total += 3
    return round(total, 1)

try:
    draft_df, history_df = load_data()
    all_owners = sorted(draft_df['Owner'].unique())
    
    st.sidebar.markdown("# 🏈 KFL")
    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])
    st.sidebar.divider()
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner].copy()
    owner_draft['Success Score'] = owner_draft.apply(lambda r: refine_score(r, draft_df), axis=1)
    owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)
    
    owner_history = history_df[history_df['Owner'] == selected_owner]

    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
        # --- DASHBOARD ---
        if sub_page == "Dashboard":
            st.title(f"📈 {selected_owner}: Dashboard")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg Success Score", f"{owner_draft['Success Score'].mean():.1f}")
            slots = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots[slots['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Round 1 Draft Slot History")
            fig_slots.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig_slots, use_container_width=True)

        # --- ARCHETYPE ---
        elif sub_page == "Archetype":
            st.title(f"🧬 {selected_owner}: Draft Archetype")
            st.subheader("Manager Tendencies")
            col_age, col_first, col_last = st.columns(3)
            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1
            valid_players = owner_draft[~owner_draft['Position'].isin(['DST', 'DEF', 'D/ST', 'DEFENSE', 'D'])]
            valid_players[['First', 'Last']] = valid_players['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))
            with col_age:
                st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
                with st.popover(f"Rank: {age_rank}/{len(league_age)}"):
                    st.table(league_age.reset_index().rename(columns={'index':'Owner','Age When Drafted':'Age'}))
            with col_first:
                cf = valid_players['First'].mode()[0] if not valid_players['First'].empty else "N/A"
                st.metric("Common First Name", cf)
                with st.popover(f"View {cf}s"):
                    st.dataframe(valid_players[valid_players['First'] == cf][['Year', 'Player Name', 'Position', 'Round']], hide_index=True)
            with col_last:
                cl = valid_players['Last'].mode()[0] if not valid_players['Last'].empty else "N/A"
                st.metric("Common Last Name", cl)
                with st.popover(f"View {cl}s"):
                    st.dataframe(valid_players[valid_players['Last'] == cl][['Year', 'Player Name', 'Position', 'Round']], hide_index=True)
            st.divider()
            st.subheader("NFL Team Reliance")
            team_counts = owner_draft['Team'].value_counts().reset_index()
            team_counts.columns = ['Team', 'Picks']
            st.plotly_chart(px.bar(team_counts.sort_values('Picks', ascending=False), x='Team', y='Picks', text='Picks', color='Picks', color_continuous_scale='Blues', height=400), use_container_width=True)
            active_teams = sorted(owner_draft[owner_draft['Team'] != 'N/A']['Team'].unique())
            sel_team = st.selectbox("Search Team History:", active_teams)
            with st.popover(f"📋 View all {sel_team} Picks"):
                st.dataframe(owner_draft[owner_draft['Team'] == sel_team][['Year', 'Round', 'Pick', 'Player Name', 'Position']].sort_values('Year', ascending=False), hide_index=True)
            st.divider()
            st.subheader("Round-by-Round Breakdown")
            selected_round = st.select_slider("Toggle Round:", options=sorted(owner_draft['Round'].unique()))
            round_df = owner_draft[owner_draft['Round'] == selected_round]
            r_c1, r_c2 = st.columns([1, 2])
            r_c1.metric("Picks Made", len(round_df))
            r_c2.dataframe(round_df[['Year', 'Pick', 'Player Name', 'Position', 'Team']], hide_index=True, use_container_width=True)
            st.divider()
            st.subheader("Player Demographics")
            demo_l, demo_r = st.columns(2)
            with demo_l:
                months_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                m_counts = valid_players['Birth Month'].value_counts().reindex(months_order, fill_value=0).reset_index()
                m_counts.columns = ['Birth Month', 'count']
                st.plotly_chart(px.bar(m_counts, x='count', y='Birth Month', orientation='h', color='count', color_continuous_scale='Sunset'), use_container_width=True)
            with demo_r:
                race_counts = valid_players['Race'].value_counts().reset_index()
                race_counts.columns = ['Race', 'count']
                st.plotly_chart(px.pie(race_counts, values='count', names='Race', hole=0.5), use_container_width=True)

        # --- PERFORMANCE ---
        elif sub_page == "Performance":
            st.title(f"🏆 {selected_owner}: Performance")
            hof, hos = st.columns(2)
            with hof:
                st.success("### ⭐ Draft Hall of Fame")
                top_5 = owner_draft.sort_values('Success Score', ascending=False).head(5)
                for i, (_, p) in enumerate(top_5.iterrows(), 1):
                    won = str(p.get('Win Championship?')).strip().upper() in ['YES', '1', '1.0', 'Y']
                    champ_bracket = "| 🏆 |" if won else "|"
                    c_pts = p.get('Championship points', 0)
                    c_text = f" | {c_pts:.1f} Final Pts" if won and c_pts > 0 else ""
                    st.markdown(f"""<div style="font-size:18px; line-height:1.8;"><b>#{i}: {p['Player Name']} ({p['Year']}) {champ_bracket}</b> Grade: {p['Grade']} ({p['Success Score']}) | {p['Points']:.0f} Pts | {p['PPG']:.1f} PPG{c_text}</div>""", unsafe_allow_html=True)
            with hos:
                st.error("### 🗑️ Draft Hall of Shame")
                busts = owner_draft[owner_draft['GP'] > 0].sort_values('Success Score', ascending=True).head(5)
                for i, (_, p) in enumerate(busts.iterrows(), 1):
                    missed = 16 - p['GP']
                    st.markdown(f"""<div style="font-size:18px; line-height:1.8;"><b>#{i}: {p['Player Name']} ({p['Year']}) |</b> Grade: {p['Grade']} ({p['Success Score']}) | {p['Points']:.0f} Pts | Missed {missed:.0f} Games</div>""", unsafe_allow_html=True)
            
            st.divider()
            
            # STABILITY FIX: Ensure size column is non-negative and has a minimum visible size
            owner_draft['Display_PPG'] = owner_draft['PPG'].clip(lower=0) + 2
            
            fig_perf = px.scatter(owner_draft, x="Round", y="Success Score", color="Grade", 
                                   size="Display_PPG", # Use the cleaned column
                                   hover_data=["Player Name", "Year", "Points"], 
                                   color_discrete_map={"S":"#FFD700", "A+":"#00FF00", "A":"#32CD32", "B":"#FFFF00", "C":"#FFA500", "D":"#FF4500", "F":"#FF0000", "F-":"#8B0000"})
            st.plotly_chart(fig_perf, use_container_width=True)
            
            st.subheader("📋 Performance Review Log")
            st.dataframe(owner_draft[['Year', 'Round', 'Player Name', 'Position', 'Points', 'PPG', 'GP', 'Success Score', 'Grade']].sort_values('Success Score', ascending=False), use_container_width=True, hide_index=True)

        # --- SCORING ---
        elif sub_page == "Scoring":
            st.title(f"🎯 {selected_owner}: Scoring Audit")
            col_pts, col_eff = st.columns(2)
            with col_pts:
                st.subheader("1. Point Source Breakdown")
                st.plotly_chart(px.pie(owner_draft.groupby('Position')['Points'].sum().reset_index(), values='Points', names='Position', hole=0.4), use_container_width=True)
            with col_eff:
                st.subheader("2. Draft Capital Efficiency")
                st.plotly_chart(px.bar(owner_draft.groupby('Round')['Points'].mean().reset_index(), x='Round', y='Points', text_auto='.0f', color='Points'), use_container_width=True)
            st.divider()
            st.subheader("3. Total Drafted Points Trend")
            trend_df = owner_draft.groupby('Year')['Points'].sum().reset_index()
            st.plotly_chart(px.line(trend_df, x='Year', y='Points', markers=True), use_container_width=True)
            st.divider()
            st.subheader("4. ⚡ Clutch Leaders (% of PIP)")
            st.dataframe(owner_draft.sort_values('% of PIP', ascending=False).head(10)[['Year', 'Player Name', '% of PIP', 'Points']], hide_index=True, use_container_width=True)
            st.divider()
            st.subheader("5. High-Water Marks (Record Book)")
            st.dataframe(owner_draft[['Year', 'Player Name', 'Position', 'Points', 'PPG', 'Grade']].sort_values('Points', ascending=False), use_container_width=True, hide_index=True)

    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Stats")
        if not owner_history.empty:
            wins = len(owner_history[owner_history['Result'].str.strip().str.upper() == 'WIN'])
            losses = len(owner_history[owner_history['Result'].str.strip().str.upper() == 'LOSS'])
            st.metric("All-Time Record", f"{wins}-{losses}")
        else:
            st.write("No career history data found.")

except Exception as e:
    st.error(f"Sync failed: {e}")
