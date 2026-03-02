import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup
st.set_page_config(page_title="KFL Archive", layout="wide")

# 2. Data Loading
@st.cache_data
def load_data():
    draft_df = pd.read_excel('Draft Data GPT (1).xlsx')
    history_df = pd.read_excel('OFFICIAL Every Game GPT.xlsx', sheet_name='Every Game')
    return draft_df, history_df

try:
    draft_df, history_df = load_data()

    # ==========================================
    # SIDEBAR: KFL BRANDING & MAIN NAV
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
        # This only shows up when Draft Room is selected
        sub_page = st.sidebar.radio(
            "DRAFT SUB-MENU",
            ["Dashboard", "Archetype", "Performance", "Scoring"]
        )
        
        st.title(f"🎯 Draft Room: {sub_page}")
        st.caption(f"Manager: {selected_owner}")

        # --- 1. DASHBOARD ---
        if sub_page == "Dashboard":
            st.subheader("At a Glance")
            # Quick stats we've already built
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg ROI Score", f"{owner_draft['ROI Score'].mean():.1f}")
            
            # Show the Draft Slot History Chart here as a "Main" visual
            slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots_df[slots_df['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Historical Draft Slot")
            fig_slots.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_slots, use_container_width=True)

        # --- 2. ARCHETYPE (Personals) ---
        elif sub_page == "Archetype":
            st.subheader("Manager Tendencies & Player Profiles")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("#### Positional Bias")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                st.plotly_chart(px.pie(pos_counts, values='count', names='Position', hole=0.4), use_container_width=True)
            with col_b:
                st.write("#### NFL Team Reliance")
                team_counts = owner_draft['Team'].value_counts().head(10).reset_index()
                st.plotly_chart(px.bar(team_counts, x='count', y='Team', orientation='h'), use_container_width=True)
            
            st.divider()
            st.write("#### Racial/Demographic Breakdown")
            race_counts = owner_draft['Race'].value_counts().reset_index()
            st.plotly_chart(px.bar(race_counts, x='Race', y='count', color='Race'), use_container_width=True)

        # --- 3. PERFORMANCE (Value) ---
        elif sub_page == "Performance":
            st.subheader("Draft Value & ROI Analysis")
            st.info("VOADP (Value Over ADP) and ROI Tiers illustrate how much 'profit' was made on each pick.")
            
            fig_roi = px.scatter(owner_draft, x="Round", y="VOADP", color="VOADP Tier", 
                                 size="Points", hover_data=["Player Name", "Year"],
                                 title="VOADP vs Draft Round")
            st.plotly_chart(fig_roi, use_container_width=True)
            
            st.write("#### ROI Tier Breakdown")
            roi_counts = owner_draft['ROI Tier'].value_counts().reset_index()
            st.plotly_chart(px.bar(roi_counts, x='ROI Tier', y='count', color='ROI Tier'), use_container_width=True)

        # --- 4. SCORING (Output) ---
        elif sub_page == "Scoring":
            st.subheader("Production & Reliability")
            sc1, sc2 = st.columns(2)
            sc1.metric("Avg PPG (Drafted Players)", f"{owner_draft['PPG'].mean():.1f}")
            sc2.metric("Total Career Games Missed", f"{owner_draft['Games missed'].sum():.0f}")

            st.write("#### Points Scored vs. Games Played")
            fig_score = px.scatter(owner_draft, x="GP", y="Points", color="Position", 
                                   hover_data=["Player Name", "Year"], size="PPG")
            st.plotly_chart(fig_score, use_container_width=True)

    # ==========================================
    # OTHER MAIN PAGES (Placeholder for now)
    # ==========================================
    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Stats")
        st.write("This area will focus on W/L records and Head-to-Head data.")

    elif main_page == "League Records":
        st.title("📜 KFL Hall of Records")
        st.write("This area will focus on all-time highs and champions.")

except Exception as e:
    st.error(f"Sync failed: {e}")
