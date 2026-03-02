import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup & "War Room" Styling
st.set_page_config(page_title="SHADYNASTY: WAR ROOM", layout="wide")

# Custom CSS to mimic the Vercel app look
st.markdown("""
    <style>
        /* Main background */
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        /* Style the metric cards */
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        /* Change font to something cleaner */
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
        }
        /* Custom header color (Neon accent) */
        h1, h2, h3 {
            color: #00ff88 !important;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        /* Style Dataframes */
        .stDataFrame {
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# 2. Data Loading
@st.cache_data
def load_data():
    df = pd.read_excel('Draft Data GPT (1).xlsx')
    return df

try:
    draft_df = load_data()

    # 3. Sidebar
    st.sidebar.title("🛡️ SHADYNASTY")
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select Manager", all_owners)
    owner_df = draft_df[draft_df['Owner'] == selected_owner]

    st.title(f"⚔️ {selected_owner}: War Room")

    # ==========================================
    # LOGIC: DRAFT SLOTS & AGE
    # ==========================================
    slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
    league_avg_slots = slots_df.groupby('Owner')['Pick'].mean().sort_values()
    owner_avg_slot = league_avg_slots[selected_owner]
    pick_rank = league_avg_slots.index.get_loc(selected_owner) + 1

    league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
    age_rank = league_age.index.get_loc(selected_owner) + 1

    # ==========================================
    # METRICS SECTION (The "Cards")
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("EXP", f"{owner_df['Year'].nunique()} Seasons")

    with col2:
        st.metric("TOTAL ASSETS", len(owner_df))

    with col3:
        st.metric("AVG DRAFT SLOT", f"{owner_avg_slot:.1f}")
        with st.popover(f"Rank: {pick_rank}"):
            ranking_table = league_avg_slots.reset_index()
            ranking_table.columns = ['Owner', 'Avg Pick']
            ranking_table.index += 1
            st.table(ranking_table.style.format({'Avg Pick': '{:.1f}'}))

    with col4:
        st.metric("TARGET AGE", f"{owner_df['Age When Drafted'].mean():.1f}")
        with st.popover(f"Rank: {age_rank}"):
            age_table = league_age.reset_index()
            age_table.columns = ['Owner', 'Avg Age']
            age_table.index += 1
            st.table(age_table.style.format({'Avg Age': '{:.1f}'}))

    st.divider()

    # ==========================================
    # CHARTS (Dark Themed)
    # ==========================================
    c_left, c_right = st.columns(2)

    with c_left:
        st.subheader("Draft Slot History")
        owner_slots = slots_df[slots_df['Owner'] == selected_owner].sort_values('Year')
        fig_slots = px.bar(owner_slots, x='Year', y='Pick', text='Pick', template="plotly_dark")
        fig_slots.update_traces(marker_color='#00ff88') # Neon Green
        fig_slots.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_slots, use_container_width=True)

    with c_right:
        st.subheader("Positional Bias")
        pos_counts = owner_df['Position'].value_counts().reset_index()
        pos_counts.columns = ['Position', 'Count']
        fig_pos = px.pie(pos_counts, values='Count', names='Position', template="plotly_dark", hole=0.5)
        fig_pos.update_traces(marker=dict(colors=['#00ff88', '#00cc77', '#009966', '#006644']))
        st.plotly_chart(fig_pos, use_container_width=True)

    # ==========================================
    # TEAM BREAKDOWN
    # ==========================================
    st.subheader("NFL Franchise Reliance")
    team_counts = owner_df['Team'].value_counts().reset_index()
    team_counts.columns = ['Team', 'Picks']
    fig_teams = px.bar(team_counts, x='Picks', y='Team', orientation='h', template="plotly_dark")
    fig_teams.update_traces(marker_color='#00ff88')
    fig_teams.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
    st.plotly_chart(fig_teams, use_container_width=True)

except Exception as e:
    st.error(f"Sync failed: {e}")
