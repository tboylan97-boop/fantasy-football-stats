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
    
    # CLEANING: Remove extra spaces and force uppercase on Teams/Owners
    draft_df['Team'] = draft_df['Team'].astype(str).str.strip().str.upper()
    draft_df['Owner'] = draft_df['Owner'].astype(str).str.strip()
    
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

    # ==========================================
    # SIDEBAR: KFL BRANDING & NAVIGATION
    # ==========================================
    st.sidebar.markdown("# 🏈 KFL")
    st.sidebar.markdown("### *Kennesaw Football League*")
    st.sidebar.divider()

    main_page = st.sidebar.radio("MAIN MENU", ["Draft Room", "Owner Statistics", "League Records"])

    st.sidebar.divider()
    all_owners = sorted(draft_df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select a Manager", all_owners)
    
    owner_draft = draft_df[draft_df['Owner'] == selected_owner]
    owner_history = history_df[history_df['Owner'] == selected_owner]

    # ==========================================
    # PAGE 1: DRAFT ROOM
    # ==========================================
    if main_page == "Draft Room":
        sub_page = st.sidebar.radio("DRAFT SUB-MENU", ["Dashboard", "Archetype", "Performance", "Scoring"])
        
        st.title(f"🎯 Draft Room: {sub_page}")
        st.caption(f"Manager: {selected_owner}")

        if sub_page == "Dashboard":
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg ROI Score", f"{owner_draft['ROI Score'].mean():.1f}")
            
            slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots_df[slots_df['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Historical Draft Slot")
            fig_slots.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig_slots, use_container_width=True)

        elif sub_page == "Archetype":
            st.subheader("Manager Tendencies & Player Profiles")

            # ROW 1: AGE & NAMES
            col_age, col_first, col_last = st.columns(3)

            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1

            with col_age:
                st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
                with st.popover(f"Rank: {age_rank}/{len(league_age)} vs League"):
                    st.table(league_age.reset_index().rename(columns={'index':'Owner','Age When Drafted':'Age'}))

            names_df = owner_draft[~owner_draft['Position'].str.upper().isin(['DST', 'DEF', 'D/ST'])].copy()
            names_df[['First', 'Last']] = names_df['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))

            with col_first:
                cf = names_df['First'].mode()[0] if not names_df['First'].empty else "N/A"
                st.metric("Common First Name", cf)
                with st.popover("View Full List"):
                    st.dataframe(names_df[names_df['First'] == cf][['Year', 'Player Name', 'Position']], hide_index=True)

            with col_last:
                cl = names_df['Last'].mode()[0] if not names_df['Last'].empty else "N/A"
                st.metric("Common Last Name", cl)
                with st.popover("View Full List"):
                    st.dataframe(names_df[names_df['Last'] == cl][['Year', 'Player Name', 'Position']], hide_index=True)

            st.divider()

            # ROW 2: TEAM RELIANCE
            st.subheader("NFL Team Reliance")
            all_nfl_teams = sorted(draft_df['Team'].unique())
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl_teams, fill_value=0).reset_index()
            team_counts.columns = ['Team', 'Picks']
            team_counts = team_counts.sort_values('Picks', ascending=False)

            fig_teams = px.bar(
                team_counts, x='Team', y='Picks', text='Picks',
                color='Picks', color_continuous_scale='Blues',
                height=500, title="Career Picks by NFL Franchise"
            )
            fig_teams.update_layout(
                xaxis_tickangle=-45, 
                xaxis_title="NFL Team",
                yaxis_title="Times Drafted",
                margin=dict(b=100),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_teams, use_container_width=True)

            st.divider()

            # ROW 3: FREQUENT FACES & POSITION BREAKDOWN
            col_freq, col_pos = st.columns(2)
            with col_freq:
                st.subheader("Frequent Faces")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player', 'Drafted']
                st.dataframe(repeats[repeats['Drafted'] >= 2], use_container_width=True, hide_index=True)

            with col_pos:
                st.subheader("Position Breakdown")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                pos_counts.columns = ['Position', 'count']
                
                # REBUILT PIE CHART (CLEANER, BOLDER TEXT)
                fig_pos = px.pie(
                    pos_counts, 
                    values='count', 
                    names='Position', 
                    hole=0.4,
                    title="Positional Strategy"
                )
                fig_pos.update_traces(
                    textinfo='label+percent', 
                    textposition='inside',
                    insidetextorientation='horizontal',
                    # This section fixes the font and color issues
                    textfont=dict(
                        family="Arial Black, Gadget, sans-serif",
                        size=16,
                        color="white" # Force all text to white
                    ),
                    marker=dict(line=dict(color='#000000', width=1.5))
                )
                
                # Add a "Shadow" effect to the text to ensure it's readable on any color
                fig_pos.update_layout(
                    showlegend=False,
                    uniformtext_minsize=14, 
                    uniformtext_mode='hide' # Hides text if it truly won't fit to prevent overlap
                )
                st.plotly_chart(fig_pos, use_container_width=True)

        elif sub_page == "Performance":
            st.subheader("Value Over ADP (VOADP) Analysis")
            st.plotly_chart(px.scatter(owner_draft, x="Round", y="VOADP", color="VOADP Tier", size="Points", hover_data=["Player Name"]), use_container_width=True)

        elif sub_page == "Scoring":
            st.subheader("Production Metrics")
            st.plotly_chart(px.scatter(owner_draft, x="GP", y="Points", color="Position", size="PPG", hover_data=["Player Name"]), use_container_width=True)

    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Performance")
        wins = len(owner_history[owner_history['Result'] == 'Win'])
        losses = len(owner_history[owner_history['Result'] == 'Loss'])
        st.metric("All-Time Record", f"{wins}-{losses}")

    elif main_page == "League Records":
        st.title("📜 KFL Hall of Records")
        st.dataframe(history_df.sort_values('Points', ascending=False).head(10)[['Year', 'Owner', 'Points']], hide_index=True)

except Exception as e:
    st.error(f"KFL App Error: {e}")
