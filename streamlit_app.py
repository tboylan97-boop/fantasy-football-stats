import streamlit as st
import pandas as pd
import plotly.express as px

# Basic Page Setup
st.set_page_config(page_title="Ultimate Fantasy League", layout="wide")

# Load Data (Cached so it's fast)
@st.cache_data
def load_data():
    # Make sure your CSV filename matches exactly what is in GitHub
    df = pd.read_csv('Draft Data GPT (1).csv')
    return df

try:
    df = load_data()

    st.title("🏆 The Ultimate Fantasy League Archive")
    st.markdown("Exploring draft ROI, player performance, and manager history since 2017.")

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Global Filters")
    owners = sorted(df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select a Manager", ["League-wide"] + list(owners))
    
    years = sorted(df['Year'].unique(), reverse=True)
    selected_year = st.sidebar.multiselect("Select Years", years, default=years)

    # Filtering the dataframe
    mask = df['Year'].isin(selected_year)
    if selected_owner != "League-wide":
        mask &= (df['Owner'] == selected_owner)
    
    filtered_df = df[mask]

    # --- TOP LEVEL METRICS ---
    st.subheader(f"Overview: {selected_owner}")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric("Total Picks", len(filtered_df))
    with m2:
        avg_roi = filtered_df['ROI Score'].mean()
        st.metric("Avg ROI Score", f"{avg_roi:.1f}")
    with m3:
        total_pts = filtered_df['Points'].sum()
        st.metric("Total Points Drafted", f"{total_pts:,.0f}")
    with m4:
        # Checking how many "League Winners" or "Elite Steals"
        steals = len(filtered_df[filtered_df['ROI Tier'].isin(['League Winner', 'Elite Steal'])])
        st.metric("Legendary Steals", steals)

    # --- VISUALIZATIONS ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.write("### ROI by Draft Round")
        # Scatter plot showing where the value was found
        fig_roi = px.scatter(
            filtered_df, 
            x="Round", 
            y="ROI Score", 
            color="ROI Tier",
            hover_data=["Player Name", "Year", "Pick"],
            title="Value Over ADP Analysis"
        )
        st.plotly_chart(fig_roi, use_container_width=True)

    with col_right:
        st.write("### Points by Position")
        # Bar chart of points per position
        fig_pos = px.bar(
            filtered_df.groupby("Position")["Points"].sum().reset_index().sort_values("Points", ascending=False),
            x="Position",
            y="Points",
            color="Position",
            title="Drafted Points by Position"
        )
        st.plotly_chart(fig_pos, use_container_width=True)

    # --- THE DATA TABLE ---
    st.write("### 🔍 Searchable Draft History")
    st.dataframe(
        filtered_df[['Year', 'Round', 'Pick', 'Player Name', 'Owner', 'ROI Score', 'ROI Tier', 'Points']],
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Waiting for data... Ensure 'Draft Data GPT (1).csv' is in your GitHub repo. Error: {e}")
