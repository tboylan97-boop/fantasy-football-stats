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
    
    # Cleaning Demographics
    if 'Birthday' in draft_df.columns:
        draft_df['Birthday'] = pd.to_datetime(draft_df['Birthday'], errors='coerce')
        draft_df['Birth Month'] = draft_df['Birthday'].dt.month_name()
    
    for col in ['Birth Month', 'Race', 'VOADP Tier']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].fillna('Unknown').astype(str)

    for col in ['Team', 'Owner', 'Position']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].astype(str).str.strip().str.upper()

    for col in ['PPG', 'GP', 'VOADP', 'Points', '% of PIP']:
        if col in draft_df.columns:
            draft_df[col] = pd.to_numeric(draft_df[col], errors='coerce').fillna(0)
    
    return draft_df, history_df

# ==========================================
# 3. ULTIMATE KFL SUCCESS FORMULA (V2 - Positional Balance)
# ==========================================
def calculate_success_score(row):
    pos = row.get('Position', 'RB')
    pts = row.get('Points', 0)
    ppg = row.get('PPG', 0)
    voadp = row.get('VOADP', 0)
    pip = row.get('% of PIP', 0)
    rd = row.get('Round', 1)
    won_champ = str(row.get('Win Championship?', '')).strip().upper() in ['YES', '1', '1.0', 'Y']

    # Production Baselines (Refined)
    if pos == 'QB': 
        baseline = 330 # High bar for QBs
    elif pos in ['K', 'DST', 'DEF', 'D/ST']: 
        baseline = 195 # RAISED: Kickers need ~12 PPG to be considered "Success"
    elif pos == 'TE':
        baseline = 175 # TEs have a lower ceiling
    else: 
        baseline = 225 # RBs and WRs

    # Production Score (60% Weight)
    prod_raw = (pts / baseline) * 60
    
    # Value / Maintenance (25% Weight)
    if rd <= 2:
        # Maintenance: Studs must maintain ~19 PPG for full credit
        value_score = min(25, (ppg / 19) * 25)
    else:
        # ROI: Late rounders must move up ~65 spots for full credit
        value_score = min(25, (max(0, voadp) / 65) * 25)

    # Clutch (15% Weight)
    clutch_score = min(15, (pip / 0.22) * 15)
    
    total = prod_raw + value_score + clutch_score
    
    # Legend Boost for 400+ points
    if pts > 400: total += 10
    
    # --- THE CHAMPIONSHIP GATE ---
    if not won_champ:
        total = min(99.9, total) # Cannot hit 100 without a ring
    else:
        if total >= 94: total = 100 # If elite and won champ, auto 100 (S)
        elif total >= 80: total += 3 # Smaller boost for champions

    return round(total, 1)

def get_grade(score):
    if score >= 100: return "S" 
    if score >= 95: return "A+"
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    if score >= 11: return "F"
    return "F-" # Reserved for the absolute zero-impact picks

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
    all_owners = sorted(draft_df['Owner'].unique())
    
    # SIDEBAR
    st.sidebar.markdown("# 🏈 KFL")
    st.sidebar.divider()
    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])
    st.sidebar.divider()
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner].copy()
    owner_history = history_df[history_df['Owner'] == selected_owner]
    
    # Run the new Formula
    owner_draft['Success Score'] = owner_draft.apply(calculate_success_score, axis=1)
    owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)

    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
        if sub_page == "Dashboard":
            st.title(f"📈 {selected_owner}: Dashboard")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg Success Score", f"{owner_draft['Success Score'].mean():.1f}")
            
            slots = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots[slots['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Round 1 Draft Slot")
            fig_slots.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig_slots, use_container_width=True)

        elif sub_page == "Archetype":
            st.title(f"🧬 {selected_owner}: Archetype")
            
            col_age, col_first, col_last = st.columns(3)
            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1
            
            valid_players = owner_draft[~owner_draft['Position'].isin(['DST', 'DEF', 'D/ST', 'DEFENSE'])].copy()
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
            
            # NFL Team Reliance
            st.subheader("NFL Team Reliance")
            team_counts = owner_draft['Team'].value_counts().reset_index()
            team_counts.columns = ['Team', 'Picks']
            st.plotly_chart(px.bar(team_counts.sort_values('Picks', ascending=False), x='Team', y='Picks', text='Picks', color='Picks', color_continuous_scale='Blues', height=400), use_container_width=True)
            
            active_teams = sorted(owner_draft[owner_draft['Team'] != 'N/A']['Team'].unique())
            sel_team = st.selectbox("View team history:", active_teams)
            with st.popover(f"📋 View all {sel_team} Picks"):
                st.dataframe(owner_draft[owner_draft['Team'] == sel_team][['Year', 'Round', 'Pick', 'Player Name', 'Position']].sort_values('Year', ascending=False), hide_index=True)

            st.divider()

            # Demographics
            demo_l, demo_r = st.columns(2)
            with demo_l:
                st.write("#### 🎂 Birth Month Frequency")
                months_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                m_counts = valid_players['Birth Month'].value_counts().reindex(months_order, fill_value=0).reset_index()
                m_counts.columns = ['Birth Month', 'count']
                st.plotly_chart(px.bar(m_counts, x='count', y='Birth Month', orientation='h', color='count', color_continuous_scale='Sunset'), use_container_width=True)
            
            with demo_r:
                st.write("#### 🧬 Racial Breakdown")
                race_counts = valid_players['Race'].value_counts().reset_index()
                race_counts.columns = ['Race', 'count']
                st.plotly_chart(px.pie(race_counts, values='count', names='Race', hole=0.5), use_container_width=True)

            st.divider()

            # Repeats & Position
            col_rep, col_p = st.columns(2)
            with col_rep:
                st.write("#### Frequent Faces")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player', 'Drafted']
                st.dataframe(repeats[repeats['Drafted'] >= 2], use_container_width=True, hide_index=True)
            with col_p:
                st.write("#### Position Strategy")
                p_counts = owner_draft['Position'].value_counts().reset_index()
                p_counts.columns = ['Position', 'count']
                st.plotly_chart(px.pie(p_counts, values='count', names='Position', hole=0.4), use_container_width=True)

      # --- PERFORMANCE (The Report Card) ---
        elif sub_page == "Performance":
            st.title(f"🏆 {selected_owner}: Performance")
            
            hof, hos = st.columns(2)
            with hof:
                st.success("### ⭐ Draft Hall of Fame")
                top_picks = owner_draft.sort_values('Success Score', ascending=False).head(5)
                # Counter for 1-5 ranking
                for i, (_, p) in enumerate(top_picks.iterrows(), 1):
                    champ_icon = "🏆" if str(p.get('Win Championship?')).strip().upper() in ['YES', '1', '1.0', 'Y'] else ""
                    # Compact string for less vertical space
                    st.markdown(f"**#{i} {p['Player Name']}** ({p['Year']}) {champ_icon}")
                    st.caption(f"Grade: **{p['Grade']}** ({p['Success Score']}) | {p['Points']:.0f} Pts | {p['PPG']:.1f} PPG")
            
            with hos:
                st.error("### 🗑️ Draft Hall of Shame")
                real_busts = owner_draft[owner_draft['GP'] > 0].sort_values('Success Score', ascending=True).head(5)
                for i, (_, p) in enumerate(real_busts.iterrows(), 1):
                    missed = 16 - p['GP']
                    v_burn = abs(p['VOADP']) if p['VOADP'] < 0 else 0
                    st.markdown(f"**#{i} {p['Player Name']}** ({p['Year']})")
                    st.caption(f"Grade: **{p['Grade']}** ({p['Success Score']}) | Missed {missed:.0f} Games | -{v_burn:.0f} Value")

            st.divider()
            
            st.subheader("Success Score by Round")
            owner_draft['bubble_size'] = owner_draft['PPG'].apply(lambda x: max(2, x))
            fig_perf = px.scatter(
                owner_draft, x="Round", y="Success Score", color="Grade", 
                size="bubble_size", hover_data=["Player Name", "Year", "Points", "Position"],
                color_discrete_map={"S":"#FFD700", "A+":"#00FF00", "A":"#7FFF00", "B":"#FFFF00", "C":"#FFA500", "D":"#FF4500", "F":"#FF0000"}
            )
            st.plotly_chart(fig_perf, use_container_width=True)

            st.subheader("📋 Performance Review Log")
            review_df = owner_draft[['Year', 'Round', 'Pick', 'Player Name', 'Position', 'Points', 'PPG', 'GP', 'Success Score', 'Grade']].sort_values('Success Score', ascending=False)
            st.dataframe(
                review_df, use_container_width=True, hide_index=True, 
                column_config={
                    "Year": st.column_config.NumberColumn("Year", format="%d", width="small"),
                    "Round": st.column_config.NumberColumn("Rd", width="small"),
                    "Pick": st.column_config.NumberColumn("Pk", width="small"),
                    "Player Name": st.column_config.TextColumn("Player", width="medium"),
                    "Position": st.column_config.TextColumn("Pos", width="small"),
                    "Points": st.column_config.NumberColumn("Total Pts", format="%.1f"),
                    "PPG": st.column_config.NumberColumn("PPG", format="%.1f"),
                    "GP": st.column_config.NumberColumn("GP", width="small"),
                    "Success Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
                    "Grade": st.column_config.TextColumn("Grade", width="small")
                }
            )

    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Stats")
        wins = len(owner_history[owner_history['Result'] == 'Win'])
        losses = len(owner_history[owner_history['Result'] == 'Loss'])
        st.metric("All-Time Record", f"{wins}-{losses}")

except Exception as e:
    st.error(f"Sync failed: {e}")
