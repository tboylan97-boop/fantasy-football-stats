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

       # --- 2. ARCHETYPE (Manager Tendencies) ---
        elif sub_page == "Archetype":
            st.subheader("Manager Tendencies & Player Profiles")
            
            # --- TOP ROW: AGE & NAME STATS ---
            col_age, col_names = st.columns(2)
            
            with col_age:
                avg_age = owner_draft['Age When Drafted'].mean()
                st.metric("Avg Player Age", f"{avg_age:.1f}")
                
                # League Age Ranking Logic (Clickable Popover)
                league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
                age_rank = league_age.index.get_loc(selected_owner) + 1
                
                with st.popover(f"🎂 View Age Rankings (Rank: {age_rank}/{len(league_age)})"):
                    st.markdown("### KFL Age Preference")
                    st.caption("Who drafts the youngest/oldest teams on average?")
                    age_ranking_table = league_age.reset_index()
                    age_ranking_table.columns = ['Owner', 'Avg Age']
                    age_ranking_table.index += 1
                    st.table(age_ranking_table.style.format({'Avg Age': '{:.1f}'}))

            with col_names:
                # Splitting names for "Fun Facts"
                # We filter out DSTs/Defenses which might not have a standard First/Last name
                valid_names = owner_draft[owner_draft['Position'] != 'DST']['Player Name'].dropna()
                first_names = valid_names.apply(lambda x: x.split()[0] if len(x.split()) > 0 else "N/A")
                last_names = valid_names.apply(lambda x: x.split()[-1] if len(x.split()) > 1 else "N/A")
                
                common_first = first_names.mode()[0] if not first_names.empty else "N/A"
                common_last = last_names.mode()[0] if not last_names.empty else "N/A"
                
                st.write(f"**Most Common First Name:** {common_first}")
                st.write(f"**Most Common Last Name:** {common_last}")

            st.divider()

            # --- SECOND ROW: TEAM RELIANCE (Full List) ---
            st.subheader("NFL Team Reliance (All 32 Teams)")
            # Get counts for ALL teams, even if 0, by using the full league team list
            all_nfl_teams = sorted(draft_df['Team'].unique())
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl_teams, fill_value=0).reset_index()
            team_counts.columns = ['NFL Team', 'Picks']
            team_counts = team_counts.sort_values('Picks', ascending=True) # Ascending for the horizontal bar chart

            fig_teams = px.bar(
                team_counts, 
                x='Picks', 
                y='NFL Team', 
                orientation='h',
                height=800, # Tall to fit all 32
                text='Picks',
                title="Career Picks by NFL Team",
                color='Picks',
                color_continuous_scale='GnBu'
            )
            st.plotly_chart(fig_teams, use_container_width=True)

            st.divider()

            # --- THIRD ROW: FREQUENT FACES (Multi-Draft Players) ---
            col_freq, col_pos = st.columns(2)
            
            with col_freq:
                st.subheader("Frequent Faces")
                st.caption("Players drafted by this owner 2 or more times")
                
                # Group by player name and count occurrences
                player_repeats = owner_draft['Player Name'].value_counts().reset_index()
                player_repeats.columns = ['Player Name', 'Times Drafted']
                # Filter for only 2+ times
                player_repeats = player_repeats[player_repeats['Times Drafted'] >= 2]
                
                if not player_repeats.empty:
                    st.dataframe(player_repeats, use_container_width=True, hide_index=True)
                else:
                    st.write("No players drafted more than once by this owner.")

            with col_pos:
                st.subheader("Positional Bias")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                fig_pos = px.pie(pos_counts, values='count', names='Position', hole=0.4)
                st.plotly_chart(fig_pos, use_container_width=True)

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
