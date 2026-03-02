import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Page Configuration
st.set_page_config(page_title="The Ultimate League Site", layout="wide")

@st.cache_data
def load_draft_data():
    # Update this filename to match exactly what you have on GitHub
    # If the file is 'Draft Data GPT (1).xlsx', use that below:
    file_path = 'Draft Data GPT (1).xlsx'
    
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        st.error(f"❌ File '{file_path}' not found in GitHub!")
        st.write("Files found in your repo:", os.listdir("."))
        st.stop()

# --- MAIN APP ---
try:
    df = load_draft_data()

    st.title("🏆 The Ultimate Fantasy Archive")
    
    # Sidebar Filters
    st.sidebar.header("Filter Statistics")
    all_owners = sorted(df['Owner'].unique())
    selected_owner = st.sidebar.selectbox("Select Manager", ["League-wide"] + list(all_owners))
    
    # Filtering Logic
    if selected_owner != "League-wide":
        display_df = df[df['Owner'] == selected_owner]
    else:
        display_df = df

    # --- TOP ROW METRICS ---
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Players Drafted", len(display_df))
    with m2:
        avg_roi = display_df['ROI Score'].mean()
        st.metric("Avg Draft ROI", f"{round(avg_roi, 2)}")
    with m3:
        total_pts = display_df['Points'].sum()
        st.metric("Total Career Points", f"{total_pts:,.0f}")

    # --- ROI CHART ---
    st.subheader(f"Draft Value Analysis: {selected_owner}")
    fig = px.scatter(
        display_df,
        x="Round",
        y="ROI Score",
        color="ROI Tier",
        size="Points",
        hover_data=["Player Name", "Year"],
        color_discrete_map={
            "League Winner": "#FFD700",
            "Elite Steal": "#C0C0C0",
            "Great Pick": "#CD7F32",
            "Bust": "#FF4B4B"
        }
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- TABLE ---
    st.subheader("Historical Draft Picks")
    st.dataframe(display_df[['Year', 'Round', 'Pick', 'Player Name', 'ROI Tier', 'Points']], use_container_width=True)

except Exception as e:
    st.warning("Connect your Excel file to begin.")
    st.info(f"Error details: {e}")
