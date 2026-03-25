import streamlit as st
import pandas as pd
import plotly.express as px
from strava_utils import load_strava_data, get_detailed_streams
from ui_components import calculate_pace_zones, generate_calendar_html

st.set_page_config(layout="wide", page_title="Training Command Center")

st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        [data-testid="stMetricLabel"] { color: #90A4AE !important; }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stWidgetLabel"] p { color: #FAFAFA; }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #4DB6AC; }
    </style>
    """, unsafe_allow_html=True)

col_title, col_sync = st.columns([4, 1])
with col_title: st.title("🏃 Training Command Center")
with col_sync:
    if st.button('🔄 Sync Data', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

summary_df = load_strava_data()

if not summary_df.empty:
    tab1, tab2, tab3 = st.tabs(["📅 Training Log", "📈 Global Trends", "🔍 Activity Details"])

    with tab1:
        st.components.v1.html(generate_calendar_html(summary_df), height=650, scrolling=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(summary_df, x='date', y='distance_km', title="Daily Mileage", 
                           color_discrete_sequence=['#4DB6AC'], template="plotly_dark"), use_container_width=True)
        with c2:
            fig_p = px.line(summary_df, x='date', y='avg_pace', title="Pace Evolution", template="plotly_dark")
            fig_p.update_traces(line_color="#90A4AE", line_width=3)
            fig_p.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p, use_container_width=True)

    with tab3:
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity:", list(options.keys()))
        run_stats = summary_df[summary_df['id'] == options[selection]].iloc[0]
        
        # --- TOP METRICS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Distance", f"{run_stats['distance_km']:.2f} km")
        m2.metric("Moving Time", f"{run_stats['moving_time_min']:.1f} min")
        
        # Format decimal pace to min:sec for the metric display
        p_min = int(run_stats['avg_pace'])
        p_sec = int((run_stats['avg_pace'] - p_min) * 60)
        m3.metric("Avg Pace", f"{p_min}:{p_sec:02d} /km")

        st.divider()

        # --- BEST 5K CALCULATION & DISPLAY ---
        # Find the best 5K pace in the dataset for zone context
        runs_near_5k = summary_df[summary_df['distance_km'].between(4.8, 5.5)]
        if not runs_near_5k.empty:
            best_5k_pace = runs_near_5k['avg_pace'].min()
            # Convert pace to total 5k time: Pace * 5
            total_seconds = best_5k_pace * 5 * 60
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            
            # Display prominently above the charts
            st.markdown(f"### 🏆 Baseline Performance")
            st.markdown(f"**Reference 5K Time:** {minutes}:{seconds:02d}  &nbsp;&nbsp; | &nbsp;&nbsp;  **Pace:** {p_min}:{p_sec:02d}/km")
            st.caption("Zones below are calibrated based on this benchmark.")
        else:
            st.caption("No 5K activities found to calibrate zones. Using default baseline.")
            best_5k_pace = 6.0 # Default fallback

        run_data = get_detailed_streams(options[selection])
        if not run_data.empty:
            # --- PACE SPLITS CHART ---
            # (Your existing splits code here...)
            
            # --- INTENSITY ZONES CHART ---
            current_zones = calculate_pace_zones(best_5k_pace)
            
            # Check pace against ranges
            def get_zone(p):
                for z in current_zones:
                    if z['min'] <= p < z['max']:
                        return z['name']
                return 'Other'

            run_data['zone'] = run_data['pace_smooth'].apply(get_zone)
            zone_time = run_data.groupby('zone')['time'].count().reset_index()
            zone_time['percent'] = (zone_time['time'] / zone_time['time'].sum()) * 100
            
            # Ensure sort order Z1 -> Z5
            z_order = [z['name'] for z in reversed(current_zones)]
            zone_time['zone'] = pd.Categorical(zone_time['zone'], categories=z_order, ordered=True)
            zone_time = zone_time.sort_values('zone')

            fig_zones = px.bar(zone_time, x='percent', y='zone', orientation='h', title="Intensity Distribution (%)",
                               color='zone', color_discrete_map={z['name']: z['color'] for z in current_zones}, template="plotly_dark")
            st.plotly_chart(fig_zones, use_container_width=True)
else:
    st.info("No activities found for 2026.")
