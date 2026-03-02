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
    
    if 'Birthday' in draft_df.columns:
        draft_df['Birthday'] = pd.to_datetime(draft_df['Birthday'], errors='coerce')
        draft_df['Birth Month'] = draft_df['Birthday'].dt.month_name()
    
    for col in ['Birth Month', 'Race', 'VOADP Tier']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].fillna('Unknown').astype(str)

    for col in ['Team', 'Owner', 'Position']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].astype(str).str.strip().str.upper()

    for col in ['PPG', 'GP', 'VOADP', 'Points', '% of PIP', 'Championship points']:
        if col in draft_df.columns:
            draft_df[col] = pd.to_numeric(draft_df[col], errors='coerce').fillna(0)
    
    return draft_df, history_df

# 3. ANALYTICS FORMULAS
def calculate_success_score(row):
    pos = row.get('Position', 'RB')
    pts = row.get('Points', 0)
    ppg = row.get('PPG', 0)
    voadp = row.get('VOADP', 0)
    pip = row.get('% of PIP', 0)
    rd = row.get('Round', 1)
    won_champ = str(row.get('Win Championship?', '')).strip().upper() in ['YES', '1', '1.0', 'Y']

    if pos == 'QB': baseline = 330
    elif pos in ['K', 'DST', 'DEF', 'D/ST']: baseline = 195
    elif pos == 'TE': baseline = 175
    else: baseline = 225
    
    prod_raw = (pts / baseline) * 60
    if rd <= 2: value_score = min(25, (ppg / 19) * 25)
    else: value_score = min(25, (max(0, voadp) / 65) * 25)

    clutch_score = min(15, (pip / 0.22) * 15)
    total = prod_raw + value_score + clutch_score
    if pts > 400: total += 10
    
    if not won_champ:
        total = min(99.9, total)
    else:
        if total >= 94: total = 100
        elif total >= 80: total += 3

    return round(total, 1)

def get_grade(score):
    if score >= 98: return "S" 
    if score >= 95: return "A+"
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
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
    st.sidebar.divider()
    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])
    st.sidebar.divider()
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner].copy()
    owner_history = history_df[history_df['Owner'] == selected_owner]
    
    owner_draft['Success Score'] = owner_draft.apply(calculate_success_score, axis=1)
    owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)

    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
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

        elif sub_page == "Archetype":
            st.title(f"🧬 {selected_owner}: Archetype")
            col_age, col_first, col_last = st.columns(3)
            valid_players = owner_draft[~owner_draft['Position'].isin(['DST', 'DEF', 'D/ST', 'DEFENSE'])].copy()
            valid_players[['First', 'Last']] = valid_players['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))
            with col_age: st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
            with col_first: st.metric("Common First Name", valid_players['First'].mode()[0] if not valid_players['First'].empty else "N/A")
            with col_last: st.metric("Common Last Name", valid_players['Last'].mode()[0] if not valid_players['Last'].empty else "N/A")
            st.divider()
            team_counts = owner_draft['Team'].value_counts().reset_index()
            team_counts.columns = ['Team', 'Picks']
            st.plotly_chart(px.bar(team_counts.sort_values('Picks', ascending=False), x='Team', y='Picks', text='Picks', color='Picks', color_continuous_scale='Blues', height=400), use_container_width=True)

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
                    c_text = f" | {c_pts:.1f} Championship Pts" if won and c_pts > 0 else ""
                    
                    st.markdown(f"""
                        <div style="font-size:18px; line-height:1.8;">
                            <b>#{i}: {p['Player Name']} ({p['Year']}) {champ_bracket}</b> 
                            Grade: {p['Grade']} ({p['Success Score']}) | {p['Points']:.0f} Pts | {p['PPG']:.1f} PPG{c_text}
                        </div>
                    """, unsafe_allow_html=True)
            
            with hos:
                st.error("### 🗑️ Draft Hall of Shame")
                busts = owner_draft[owner_draft['GP'] > 0].sort_values('Success Score', ascending=True).head(5)
                for i, (_, p) in enumerate(busts.iterrows(), 1):
                    v_burn = abs(p['VOADP']) if p['VOADP'] < 0 else 0
                    st.markdown(f"""
                        <div style="font-size:18px; line-height:1.8;">
                            <b>#{i}: {p['Player Name']} ({p['Year']}) |</b> 
                            Grade: {p['Grade']} ({p['Success Score']}) | {p['Points']:.0f} Pts | {p['PPG']:.1f} PPG | -{v_burn:.0f} Value
                        </div>
                    """, unsafe_allow_html=True)

            st.divider()
            owner_draft['bubble_size'] = owner_draft['PPG'].apply(lambda x: max(2, x))
            fig_perf = px.scatter(owner_draft, x="Round", y="Success Score", color="Grade", size="bubble_size", hover_data=["Player Name", "Year", "Points", "Position"], 
                                   color_discrete_map={"S":"#FFD700", "A+":"#00FF00", "A":"#32CD32", "B":"#FFFF00", "C":"#FFA500", "D":"#FF4500", "F":"#FF0000", "F-":"#8B0000"})
            st.plotly_chart(fig_perf, use_container_width=True)
            st.subheader("📋 Performance Review Log")
            review_df = owner_draft[['Year', 'Round', 'Pick', 'Player Name', 'Position', 'Points', 'PPG', 'GP', 'Success Score', 'Grade']].sort_values('Success Score', ascending=False)
            st.dataframe(review_df, use_container_width=True, hide_index=True, column_config={"Year": st.column_config.NumberColumn("Year", format="%d", width="small"), "Round": st.column_config.NumberColumn("Rd", width="small"), "Pick": st.column_config.NumberColumn("Pk", width="small"), "Player Name": st.column_config.TextColumn("Player", width="medium"), "Position": st.column_config.TextColumn("Pos", width="small"), "Points": st.column_config.NumberColumn("Total Pts", format="%.1f"), "PPG": st.column_config.NumberColumn("PPG", format="%.1f"), "GP": st.column_config.NumberColumn("GP", width="small"), "Success Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"), "Grade": st.column_config.TextColumn("Grade", width="small")})

except Exception as e:
    st.error(f"Sync failed: {e}")
