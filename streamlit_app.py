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
    
    # Demographics & Date Handling
    if 'Birthday' in draft_df.columns:
        draft_df['Birthday'] = pd.to_datetime(draft_df['Birthday'], errors='coerce')
        draft_df['Birth Month'] = draft_df['Birthday'].dt.month_name()
    
    for col in ['Birth Month', 'Race', 'VOADP Tier']:
        if col in draft_df.columns:
            draft_df[col] = draft_df[col].fillna('Unknown').astype(str)

    # Clean Team, Owner, and Position
    for col in ['Team', 'Owner', 'Position']:
        draft_df[col] = draft_df[col].astype(str).str.strip().str.upper()
    
    return draft_df, history_df

# SUCCESS SCORE LOGIC
def calculate_success_score(row):
    # 60% Season Production (PPG * GP)
    ppg = row.get('PPG', 0)
    gp = row.get('GP', 0)
    reg_score = min(60, ((ppg * gp) / 210) * 60)
    
    # 25% Draft Value (VOADP)
    voadp = row.get('VOADP', 0)
    roi_score = min(25, (max(0, voadp) / 50) * 25)
    
    # 15% Postseason Impact (% of PIP)
    pip = row.get('% of PIP', 0)
    clutch_score = min(15, (pip / 0.20) * 15)
    
    return round(reg_score + roi_score + clutch_score, 1)

def get_grade(score):
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"

try:
    draft_df, history_df = load_data()
    all_owners = sorted(draft_df['Owner'].unique())
    
    # SIDEBAR
    st.sidebar.markdown("# 🏈 KFL")
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    main_page = st.sidebar.radio("MENU", ["Draft Room", "Owner Statistics", "League Records"])
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner].copy()
    owner_draft['Success Score'] = owner_draft.apply(calculate_success_score, axis=1)
    owner_draft['Grade'] = owner_draft['Success Score'].apply(get_grade)

    if main_page == "Draft Room":
        sub = st.sidebar.radio("SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
        # --- ARCHETYPE TAB (The "Identity") ---
        if sub == "Archetype":
            st.title(f"🧬 {selected_owner}: Draft Archetype")
            st.caption("Scouting report based on career draft tendencies.")
            
            # Demographics Section
            d1, d2 = st.columns(2)
            with d1:
                st.write("#### 🎂 Birth Month Frequency")
                m_counts = owner_draft['Birth Month'].value_counts().reset_index()
                st.plotly_chart(px.bar(m_counts, x='count', y='Birth Month', orientation='h', color_continuous_scale='Sunset'), use_container_width=True)
            with d2:
                st.write("#### 🧬 Racial Breakdown")
                valid_r = owner_draft[~owner_draft['Position'].isin(['DST', 'DEF', 'D/ST'])]
                st.plotly_chart(px.pie(valid_r, names='Race', hole=0.4), use_container_width=True)

        # --- PERFORMANCE TAB (The "Report Card") ---
        elif sub == "Performance":
            st.title(f"🏆 {selected_owner}: Performance Analytics")
            st.caption("How well did the picks actually perform? (60% Season | 25% Value | 15% Playoff)")

            # Hall of Fame / Hall of Shame
            hof, hos = st.columns(2)
            with hof:
                st.success("### ⭐ Draft Hall of Fame")
                top_picks = owner_draft.sort_values('Success Score', ascending=False).head(5)
                for _, p in top_picks.iterrows():
                    st.write(f"**{p['Player Name']} ({p['Year']})** - {p['Grade']} ({p['Success Score']})")
            
            with hos:
                st.error("### 🗑️ Draft Hall of Shame")
                bust_picks = owner_draft.sort_values('Success Score', ascending=True).head(5)
                for _, p in bust_picks.iterrows():
                    st.write(f"**{p['Player Name']} ({p['Year']})** - {p['Grade']} ({p['Success Score']})")

            st.divider()
            
            # Detailed VOADP Chart
            st.subheader("Value Over ADP (VOADP) by Round")
            fig_voadp = px.scatter(owner_draft, x="Round", y="VOADP", color="Grade", 
                                   size="Success Score", hover_data=["Player Name", "Year"])
            st.plotly_chart(fig_voadp, use_container_width=True)

            with st.expander("View Full Grade History"):
                st.dataframe(owner_draft[['Year', 'Round', 'Player Name', 'Position', 'Success Score', 'Grade']].sort_values('Success Score', ascending=False), hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
