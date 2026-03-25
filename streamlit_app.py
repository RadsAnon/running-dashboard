import streamlit as st
import pandas as pd
import plotly.express as px
from strava_utils import load_strava_data, get_detailed_streams
from ui_components import calculate_pace_zones, generate_calendar_html, format_pace

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
        
        p_min = int(run_stats['avg_pace'])
        p_sec = int((run_stats['avg_pace'] - p_min) * 60)
        m3.metric("Avg Pace", f"{p_min}:{p_sec:02d} /km")

        st.divider()

        # --- BEST 5K CALCULATION ---
        runs_near_5k = summary_df[summary_df['distance_km'].between(4.8, 5.5)]
        if not runs_near_5k.empty:
            best_5k_pace = runs_near_5k['avg_pace'].min()
            total_seconds = best_5k_pace * 5 * 60
            b_min, b_sec = int(total_seconds // 60), int(total_seconds % 60)
            
            st.markdown(f"### 🏆 Baseline Performance")
            st.markdown(f"**Reference 5K Time:** {b_min}:{b_sec:02d} | **Pace:** {format_pace(best_5k_pace)}/km")
            st.caption("Zones below are calibrated based on this benchmark.")
        else:
            st.caption("No 5K activities found. Using default baseline (6:00/km).")
            best_5k_pace = 6.0

        run_data = get_detailed_streams(options[selection])
        if not run_data.empty:
            # --- 1. PACE SPLITS CHART (FIXED) ---
            run_data['km_bin'] = (run_data['dist_km']).astype(int) + 1
            splits = []
            for km, group in run_data.groupby('km_bin'):
                d_diff = (group['dist_m'].max() - group['dist_m'].min()) / 1000
                t_diff = (group['time'].max() - group['time'].min()) / 60
                if d_diff > 0.1:
                    pace = t_diff / d_diff
                    splits.append({'KM': f"KM {km}", 'Pace': pace, 'Label': f"{format_pace(pace)}"})
            
            df_splits = pd.DataFrame(splits)
            fig_splits = px.bar(df_splits, x='Pace', y='KM', orientation='h', 
                                text='Label', title="Pace Splits", 
                                color_discrete_sequence=['#4DB6AC'], template="plotly_dark")
            fig_splits.update_traces(textposition='outside')
            fig_splits.update_layout(yaxis={'autorange': 'reversed'}, xaxis_title="Pace (min/km)")
            st.plotly_chart(fig_splits, use_container_width=True)

            st.divider()

            # --- 2. INTENSITY ZONES CHART ---
            current_zones = calculate_pace_zones(best_5k_pace)
            # Create labels that include the range: "Z3: Tempo (5:00-5:30)"
            zone_label_map = {z['name']: f"{z['name']} ({z['range']})" for z in current_zones}

            def get_zone_name(p):
                for z in current_zones:
                    if z['min'] <= p < z['max']: return z['name']
                return 'Other'

            run_data['raw_zone'] = run_data['pace_smooth'].apply(get_zone_name)
            run_data['display_zone'] = run_data['raw_zone'].map(zone_label_map)
            
            zone_time = run_data.groupby('display_zone')['time'].count().reset_index()
            zone_time['percent'] = (zone_time['time'] / zone_time['time'].sum()) * 100
            
            z_display_order = [zone_label_map[z['name']] for z in reversed(current_zones)]
            zone_time['display_zone'] = pd.Categorical(zone_time['display_zone'], categories=z_display_order, ordered=True)
            zone_time = zone_time.sort_values('display_zone')

            fig_zones = px.bar(zone_time, x='percent', y='display_zone', orientation='h', 
                               title="Time in Intensity Zones (%)",
                               color='display_zone', 
                               color_discrete_map={zone_label_map[z['name']]: z['color'] for z in current_zones}, 
                               template="plotly_dark")
            
            fig_zones.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Percentage of Run")
            st.plotly_chart(fig_zones, use_container_width=True)
else:
    st.info("No activities found for 2026.")
