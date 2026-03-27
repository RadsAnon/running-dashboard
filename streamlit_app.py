import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from strava_utils import load_strava_data, get_detailed_streams
from ui_components import calculate_pace_zones, generate_calendar_html, format_pace

st.set_page_config(layout="wide", page_title="Training Command Center")

# --- SIDEBAR FILTERS ---
st.sidebar.header("Global Filters")
summary_df = load_strava_data()

if not summary_df.empty:
    # Set default date range (Last 30 days)
    min_date = summary_df['date'].min()
    max_date = summary_df['date'].max()
    default_start = max_date - timedelta(days=30)

    start_date = st.sidebar.date_input("Start Date", value=default_start, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

    # Filter the dataframe based on selection
    filtered_df = summary_df[(summary_df['date'] >= start_date) & (summary_df['date'] <= end_date)]
else:
    filtered_df = pd.DataFrame()

# --- MAIN UI ---
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        [data-testid="stMetricLabel"] { color: #90A4AE !important; }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #4DB6AC; }
    </style>
    """, unsafe_allow_html=True)

col_title, col_sync = st.columns([4, 1])
with col_title: st.title("🏃 Training Command Center")
with col_sync:
    if st.button('🔄 Sync', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if not filtered_df.empty:
    tab1, tab2, tab3 = st.tabs(["📅 Log", "📈 Trends", "🔍 Details"])

    with tab1:
        # Calendar usually shows the last 5 weeks regardless of filter for continuity
        st.components.v1.html(generate_calendar_html(summary_df), height=600, scrolling=True)

    with tab2:
        st.subheader(f"Insights: {start_date.strftime('%b %d')} — {end_date.strftime('%b %d')}")
        
        # Summary Metrics for the filtered period
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Distance", f"{filtered_df['distance_km'].sum():.1f} km")
        m2.metric("Avg Weekly Vol", f"{(filtered_df['distance_km'].sum() / max(1, (end_date - start_date).days / 7)):.1f} km/wk")
        avg_p = filtered_df['avg_pace'].mean()
        m3.metric("Avg Pace", f"{format_pace(avg_p)} /km")

        c1, c2 = st.columns(2)
        with c1:
            fig_m = px.bar(filtered_df, x='date', y='distance_km', title="Daily Mileage", 
                           color_discrete_sequence=['#4DB6AC'], template="plotly_dark")
            fig_m.update_layout(xaxis_title=None, yaxis_title="km")
            fig_m.update_xaxes(fixedrange=True)
            fig_m.update_yaxes(fixedrange=True)
            st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False})
            
        with c2:
            fig_p = px.line(filtered_df, x='date', y='avg_pace', title="Pace Evolution", template="plotly_dark")
            fig_p.update_traces(line_color="#90A4AE", line_width=3, mode='lines+markers')
            fig_p.update_yaxes(autorange="reversed", fixedrange=True, title="min/km")
            fig_p.update_xaxes(fixedrange=True, title=None)
            st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False})

    with tab3:
        # Use summary_df here so you can pick any activity ever recorded, 
        # not just ones in the filtered range
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity:", list(options.keys()))
        # ... (Rest of your tab3 logic remains the same) ...

else:
    st.info("No activities found for the selected date range.")
