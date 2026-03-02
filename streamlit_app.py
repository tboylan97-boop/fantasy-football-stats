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
    
    # Aggressive Cleaning for Demographics
    if 'Birthday' in draft_df.columns:
        draft_df['Birthday'] = pd.to_datetime(draft_df['Birthday'], errors='coerce')
        draft_df['Birth Month'] = draft_df['Birthday'].dt.month_name()
    
    for col in ['Birth Month', 'Race', 'VOADP Tier']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].astype(str).str.strip().replace(['nan', 'None', 'null'], 'Unknown')

    for col in ['Team', 'Owner', 'Position']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].astype(str).str.strip().str.upper()

    for col in ['PPG', 'GP', 'VOADP', 'Points', '% of PIP', 'Championship points']:
        if col in draft_df.columns:
            draft_df[col] = pd.to_numeric(draft_df[col], errors='coerce').fillna(0)
    
    return draft_df, history_df

# 3. CONTEXTUAL ANALYTICS FORMULA
def calculate_success_score(row, full_data):
    year = row.get('Year')
    pos = row.get('Position', 'RB')
    pts = row.get('Points', 0)
    ppg = row.get('PPG', 0)
    voadp = row.get('VOADP', 0)
    pip = row.get('% of PIP', 0)
    rd = row.get('Round', 1)
    won_champ = str(row.get('Win Championship?', '')).strip().upper() in ['YES', '1', '1.0', 'Y']

    # B1: Absolute Production (30%)
    if pos == 'QB': baseline = 330
    elif pos in ['K', 'DST', 'DEF', 'D/ST']: baseline = 195
    elif pos == 'TE': baseline = 175
    else: baseline = 225
    abs_score = (pts / baseline) * 30

    # B2: Yearly Dominance (30%)
    yearly_pos_data = full_data[(full_data['Year'] == year) & (full_data['Position'] == pos)]
    yearly_max = yearly_pos_data['Points'].max() if not yearly_pos_data.empty else 0
    rel_score = (pts / yearly_max) * 30 if yearly_max > 0 else abs_score

    # B3: Value/Maintenance (25%)
    if rd <= 2: value_score = min(25, (ppg / 19) * 25)
    else: value_score = min(25, (max(0, voadp) / 65) * 25)

    # B4: Clutch (15%)
    clutch_score = min(15, (pip / 0.22) * 15)
    
    total = abs_score + rel_score + value_score + clutch_score
    if pts > 400: total += 10
    
    if not won_champ: total = min(99.9, total)
    else:
        if total >= 94: total = 100
        elif total >= 80: total += 3
    return round(total, 1)

def get_grade(score):
    if score >= 100: return "S" 
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

try:
    draft_df, history_df = load_data()
    all_owners = sorted(draft_df['Owner'].unique())
    
    st.sidebar.markdown("# 🏈 KFL")
    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])
    st.sidebar.divider()
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner].copy()
    owner_draft['Success Score'] = owner_draft.apply(lambda row: calculate_success_score(row, draft_df), axis=1)
    owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)
    
    owner_history = history_df[history_df['Owner'] == selected_owner]

    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
        # --- SUB-TAB 1: DASHBOARD ---
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

        # --- SUB-TAB 2: ARCHETYPE (FULL RESTORATION) ---
        elif sub_page == "Archetype":
            st.title(f"🧬 {selected_owner}: Draft Archetype")
            
            # 1. Names & Age Section
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
            
            # 2. NFL Team Reliance
            st.subheader("NFL Team Reliance")
            team_counts = owner_draft['Team'].value_counts().reset_index()
            team_counts.columns = ['Team', 'Picks']
            st.plotly_chart(px.bar(team_counts.sort_values('Picks', ascending=False), 
                                   x='Team', y='Picks', text='Picks', 
                                   title=f"Distribution of Picks by NFL Team",
                                   color='Picks', color_continuous_scale='Blues', height=400), use_container_width=True)
            active_teams = sorted(owner_draft[owner_draft['Team'] != 'N/A']['Team'].unique())
            sel_team = st.selectbox("Search Team History:", active_teams)
            with st.popover(f"📋 View all {sel_team} Picks"):
                st.dataframe(owner_draft[owner_draft['Team'] == sel_team][['Year', 'Round', 'Pick', 'Player Name', 'Position']].sort_values('Year', ascending=False), hide_index=True)

            st.divider()

            # 3. Round Slider
            st.subheader("Round-by-Round Breakdown")
            available_rounds = sorted(owner_draft['Round'].unique())
            selected_round = st.select_slider("Toggle Round to see picks:", options=available_rounds)
            round_df = owner_draft[owner_draft['Round'] == selected_round]
            r_c1, r_c2 = st.columns([1, 2])
            r_c1.metric("Picks Made", len(round_df))
            r_c1.metric("Avg PPG", f"{round_df['PPG'].mean():.1f}")
            r_c2.dataframe(round_df[['Year', 'Pick', 'Player Name', 'Position', 'Team']], hide_index=True, use_container_width=True)

            st.divider()

            # 4. Demographics Section
            st.subheader("Player Demographics")
            demo_l, demo_r = st.columns(2)
            with demo_l:
                st.write("#### 🎂 Birth Month Frequency")
                months_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                m_counts = valid_players['Birth Month'].value_counts().reindex(months_order, fill_value=0).reset_index()
                m_counts.columns = ['Birth Month', 'count']
                st.plotly_chart(px.bar(m_counts, x='count', y='Birth Month', orientation='h', 
                                       title="Drafted Players by Birth Month",
                                       color='count', color_continuous_scale='Sunset'), use_container_width=True)
                sel_month = st.selectbox("View players born in:", [m for m in months_order if m in valid_players['Birth Month'].unique()])
                with st.popover(f"🎈 View {sel_month} Birthdays"):
                    st.dataframe(valid_players[valid_players['Birth Month'] == sel_month][['Year', 'Player Name', 'Position', 'Round']], hide_index=True)
            
            with demo_r:
                st.write("#### 🧬 Racial Breakdown")
                race_counts = valid_players['Race'].value_counts().reset_index()
                race_counts.columns = ['Race', 'count']
                st.plotly_chart(px.pie(race_counts, values='count', names='Race', hole=0.5, 
                                       title="Drafted Players by Race"), use_container_width=True)
                sel_race = st.selectbox("View players by race:", sorted(valid_players['Race'].unique()))
                with st.popover(f"🧬 View {sel_race} Players"):
                    st.dataframe(valid_players[valid_players['Race'] == sel_race][['Year', 'Player Name', 'Position', 'Round']], hide_index=True)

            st.divider()

            # 5. Position Strategy
            st.subheader("Position Strategy")
            col_rep, col_p = st.columns(2)
            with col_rep:
                st.write("#### Frequent Faces")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player', 'Drafted']
                st.dataframe(repeats[repeats['Drafted'] >= 2], use_container_width=True, hide_index=True)
            with col_p:
                st.write("#### Strategy Tally")
                p_counts = owner_draft['Position'].value_counts().reset_index()
                p_counts.columns = ['Position', 'count']
                st.plotly_chart(px.pie(p_counts, values='count', names='Position', hole=0.4, 
                                       title="Picks by Position"), use_container_width=True)
                sel_p = st.selectbox("Search Position History:", sorted(owner_draft['Position'].unique()))
                with st.popover(f"🚀 View all {sel_p}s"):
                    st.dataframe(owner_draft[owner_draft['Position'] == sel_p][['Year', 'Round', 'Pick', 'Player Name', 'Team']].sort_values('Year', ascending=False), hide_index=True)

        # --- SUB-TAB 3: PERFORMANCE ---
       # --- PERFORMANCE (Refined Positional Weighting) ---
        elif sub_page == "Performance":
            st.title(f"🏆 {selected_owner}: Performance")
            
            # --- UPDATED FORMULA LOGIC (Internal to this tab) ---
           def refine_score(row, full_data):
                pos = row.get('Position', 'RB')
                pts = row.get('Points', 0)
                ppg = row.get('PPG', 0)
                voadp = row.get('VOADP', 0)
                pip = row.get('% of PIP', 0)
                rd = row.get('Round', 1)
                won_champ = str(row.get('Win Championship?', '')).strip().upper() in ['YES', '1', '1.0', 'Y']

                # B1: Absolute (30%)
                if pos == 'QB': baseline = 340
                elif pos in ['K', 'DST', 'DEF', 'D/ST']: baseline = 220 
                elif pos == 'TE': baseline = 180
                else: baseline = 230 
                abs_score = (pts / baseline) * 30

                # B2: Yearly Dominance (30%)
                yearly_pos_data = full_data[(full_data['Year'] == row['Year']) & (full_data['Position'] == pos)]
                yearly_max = yearly_pos_data['Points'].max() if not yearly_pos_data.empty else 0
                rel_score = (pts / yearly_max) * 30 if yearly_max > 0 else abs_score
                
                # POSITION PENALTY: Kickers/DST dominance is worth half as much as Skill dominance
                if pos in ['K', 'DST', 'DEF', 'D/ST']:
                    rel_score = rel_score * 0.4 

                # B3: Value/Maintenance (25%)
                if rd <= 2:
                    value_score = min(25, (ppg / 20) * 25)
                else:
                    # HEAVY ROI: Reward late round hits like Kenneth Walker (7th round)
                    # We boost the VOADP impact for RBs/WRs taken late
                    multiplier = 1.5 if pos in ['RB', 'WR', 'TE'] else 1.0
                    value_score = min(25, (max(0, voadp) / 60) * 25 * multiplier)

                # B4: Clutch (15%)
                clutch_score = min(15, (pip / 0.22) * 15)
                
                total = abs_score + rel_score + value_score + clutch_score
                if pts > 400: total += 10
                
                # --- THE FINAL POLISH ---
                if pos in ['K', 'DST', 'DEF', 'D/ST'] and not won_champ:
                    total = min(78, total) # Cap elite kickers at a high C/low B

                if not won_champ:
                    total = min(99.9, total)
                else:
                    if total >= 94: total = 100
                    elif total >= 80: total += 3
                return round(total, 1)

            # Re-apply refined logic
            owner_draft['Success Score'] = owner_draft.apply(lambda r: refine_score(r, draft_df), axis=1)
            owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)

            hof, hos = st.columns(2)
            with hof:
                st.success("### ⭐ Draft Hall of Fame")
                top_5 = owner_draft.sort_values('Success Score', ascending=False).head(5)
                for i, (_, p) in enumerate(top_5.iterrows(), 1):
                    won = str(p.get('Win Championship?')).strip().upper() in ['YES', '1', '1.0', 'Y']
                    champ_bracket = "| 🏆 |" if won else "|"
                    c_pts = p.get('Championship points', 0)
                    c_text = f" | {c_pts:.1f} Championship Pts" if won and c_pts > 0 else ""
                    st.markdown(f"""<div style="font-size:18px; line-height:1.8;"><b>#{i}: {p['Player Name']} ({p['Year']}) {champ_bracket}</b> Grade: {p['Grade']} ({p['Success Score']}) | {p['Points']:.0f} Pts | {p['PPG']:.1f} PPG{c_text}</div>""", unsafe_allow_html=True)
            
            with hos:
                st.error("### 🗑️ Draft Hall of Shame")
                busts = owner_draft[owner_draft['GP'] > 0].sort_values('Success Score', ascending=True).head(5)
                for i, (_, p) in enumerate(busts.iterrows(), 1):
                    v_burn = abs(p['VOADP']) if p['VOADP'] < 0 else 0
                    st.markdown(f"""<div style="font-size:18px; line-height:1.8;"><b>#{i}: {p['Player Name']} ({p['Year']}) |</b> Grade: {p['Grade']} ({p['Success Score']}) | {p['Points']:.0f} Pts | {p['PPG']:.1f} PPG | -{v_burn:.0f} Value</div>""", unsafe_allow_html=True)
            
            st.divider()
            
            owner_draft['bubble_size'] = owner_draft['PPG'].apply(lambda x: max(2, x))
            fig_perf = px.scatter(owner_draft, x="Round", y="Success Score", color="Grade", size="bubble_size", hover_data=["Player Name", "Year", "Points", "Position"], 
                                   color_discrete_map={"S":"#FFD700", "A+":"#00FF00", "A":"#32CD32", "B":"#FFFF00", "C":"#FFA500", "D":"#FF4500", "F":"#FF0000", "F-":"#8B0000"})
            st.plotly_chart(fig_perf, use_container_width=True)
            
            st.subheader("📋 Performance Review Log")
            review_df = owner_draft[['Year', 'Round', 'Pick', 'Player Name', 'Position', 'Points', 'PPG', 'GP', 'Success Score', 'Grade']].sort_values('Success Score', ascending=False)
            st.dataframe(review_df, use_container_width=True, hide_index=True, column_config={"Year": st.column_config.NumberColumn("Year", format="%d", width="small"), "Success Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f")})

    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Stats")
        wins = len(owner_history[owner_history['Result'] == 'Win'])
        losses = len(owner_history[owner_history['Result'] == 'Loss'])
        st.metric("All-Time Record", f"{wins}-{losses}")

except Exception as e:
    st.error(f"Sync failed: {e}")
