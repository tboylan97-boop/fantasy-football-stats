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

# Helper Function for Name Logic
def get_clean_names(name):
    if pd.isna(name):
        return "", ""
    
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V', 'JR.', 'SR.']
    parts = str(name).split()
    
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    
    # Check if the last part is a suffix
    if parts[-1].upper() in suffixes:
        # Last name is the last two words (e.g., Thomas Jr.)
        last_name = " ".join(parts[-2:])
        first_name = " ".join(parts[:-2]) if len(parts) > 2 else parts[0]
    else:
        # Standard last word logic
        last_name = parts[-1]
        first_name = " ".join(parts[:-1])
        
    return first_name, last_name

try:
    draft_df, history_df = load_data()

    # ==========================================
    # SIDEBAR: KFL BRANDING & NAVIGATION
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
        sub_page = st.sidebar.radio(
            "DRAFT SUB-MENU",
            ["Dashboard", "Archetype", "Performance", "Scoring"]
        )
        
        st.title(f"🎯 Draft Room: {sub_page}")
        st.caption(f"Manager: {selected_owner}")

        # --- 1. DASHBOARD ---
        if sub_page == "Dashboard":
            st.subheader("At a Glance")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Picks", len(owner_draft))
            c2.metric("Draft Years", owner_draft['Year'].nunique())
            c3.metric("Avg ROI Score", f"{owner_draft['ROI Score'].mean():.1f}")
            
            slots_df = draft_df[draft_df['Round'] == 1].groupby(['Owner', 'Year'])['Pick'].first().reset_index()
            fig_slots = px.bar(slots_df[slots_df['Owner'] == selected_owner], x='Year', y='Pick', text='Pick', title="Historical Draft Slot")
            fig_slots.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_slots, use_container_width=True)

        # --- 2. ARCHETYPE (Tendencies) ---
        elif sub_page == "Archetype":
            st.subheader("Manager Tendencies & Player Profiles")

            # --- ROW 1: AGE & NAME POP-UPS ---
            col_age, col_first, col_last = st.columns(3)

            # Age Ranking Logic
            league_age = draft_df.groupby('Owner')['Age When Drafted'].mean().sort_values()
            age_rank = league_age.index.get_loc(selected_owner) + 1

            with col_age:
                st.metric("Avg Player Age", f"{owner_draft['Age When Drafted'].mean():.1f}")
                with st.popover(f"Rank: {age_rank}/{len(league_age)} vs League"):
                    st.markdown("### League Average Age")
                    age_table = league_age.reset_index()
                    age_table.columns = ['Owner', 'Avg Age']
                    age_table.index += 1
                    st.table(age_table.style.format({'Avg Age': '{:.1f}'}))

            # --- REFINED NAME ANALYSIS ---
            # Filter out D/ST and non-player rows
            names_df = owner_draft[~owner_draft['Position'].str.upper().isin(['DST', 'DEF', 'D/ST', 'DEFENSE'])].copy()
            names_df = names_df.dropna(subset=['Player Name'])
            
            # Apply our new suffix-aware logic
            names_df[['First', 'Last']] = names_df['Player Name'].apply(lambda x: pd.Series(get_clean_names(x)))

            with col_first:
                if not names_df['First'].empty:
                    common_first = names_df['First'].mode()[0]
                    st.metric("Common First Name", common_first)
                    with st.popover("View All Players"):
                        st.write(f"Players named **{common_first}** drafted by {selected_owner}:")
                        # Show distinct players and their first draft year
                        matches = names_df[names_df['First'] == common_first][['Year', 'Player Name', 'Position']].sort_values('Year')
                        st.dataframe(matches, hide_index=True, use_container_width=True)
                else:
                    st.metric("Common First Name", "N/A")

            with col_last:
                if not names_df['Last'].empty:
                    common_last = names_df['Last'].mode()[0]
                    st.metric("Common Last Name", common_last)
                    with st.popover("View All Players"):
                        st.write(f"Players with last name **{common_last}** drafted by {selected_owner}:")
                        matches = names_df[names_df['Last'] == common_last][['Year', 'Player Name', 'Position']].sort_values('Year')
                        st.dataframe(matches, hide_index=True, use_container_width=True)
                else:
                    st.metric("Common Last Name", "N/A")

            st.divider()

            # --- ROW 2: TEAM RELIANCE (Full 32 Teams) ---
            st.subheader("NFL Team Reliance")
            all_nfl_teams = sorted(draft_df['Team'].unique())
            team_counts = owner_draft['Team'].value_counts().reindex(all_nfl_teams, fill_value=0).reset_index()
            team_counts.columns = ['NFL Team', 'Picks']
            team_counts = team_counts.sort_values('Picks', ascending=True)

            fig_teams = px.bar(team_counts, x='Picks', y='NFL Team', orientation='h', height=800, text='Picks', color='Picks', color_continuous_scale='Blues')
            st.plotly_chart(fig_teams, use_container_width=True)

            st.divider()

            # --- ROW 3: FREQUENT FACES ---
            col_freq, col_pos = st.columns(2)
            with col_freq:
                st.subheader("Frequent Faces")
                st.caption("Players drafted by this owner more than once")
                repeats = owner_draft['Player Name'].value_counts().reset_index()
                repeats.columns = ['Player Name', 'Times Drafted']
                repeats = repeats[repeats['Times Drafted'] >= 2]
                if not repeats.empty:
                    st.dataframe(repeats, use_container_width=True, hide_index=True)
                else:
                    st.write("No players drafted 2+ times.")

            with col_pos:
                st.subheader("Position Breakdown")
                pos_counts = owner_draft['Position'].value_counts().reset_index()
                st.plotly_chart(px.pie(pos_counts, values='count', names='Position', hole=0.4), use_container_width=True)

        # --- 3. PERFORMANCE & 4. SCORING (Placeholders) ---
        elif sub_page == "Performance":
            st.subheader("Draft Value & ROI Analysis")
            st.plotly_chart(px.scatter(owner_draft, x="Round", y="VOADP", color="VOADP Tier", hover_data=["Player Name"]), use_container_width=True)

        elif sub_page == "Scoring":
            st.subheader("Production & Reliability")
            st.plotly_chart(px.scatter(owner_draft, x="GP", y="Points", color="Position", size="PPG"), use_container_width=True)

    # ==========================================
    # OTHER MAIN PAGES
    # ==========================================
    elif main_page == "Owner Statistics":
        st.title(f"📊 {selected_owner}: Career Performance")
        # Add basic record logic here
        
    elif main_page == "League Records":
        st.title("📜 KFL Hall of Records")
        st.dataframe(history_df.sort_values('Points', ascending=False).head(10)[['Year', 'Week', 'Owner', 'Points']], hide_index=True)

except Exception as e:
    st.error(f"KFL App Error: {e}")
