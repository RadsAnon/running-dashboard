import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from strava_utils import load_strava_data, get_detailed_streams
from ui_components import calculate_pace_zones, generate_calendar_html, format_pace

st.set_page_config(layout="wide", page_title="Training Command Center")

# --- DATA LOADING ---
summary_df = load_strava_data()

# Global date standardization
if not summary_df.empty:
    summary_df['date'] = pd.to_datetime(summary_df['date']).dt.date

# --- MAIN UI STYLE ---
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        [data-testid="stMetricLabel"] { color: #90A4AE !important; }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #4DB6AC; }
    </style>
    """, unsafe_allow_html=True)

col_title, col_sync = st.columns([4, 1])
with col_title: 
    st.title("🏃 Training Command Center")
with col_sync:
    if st.button('🔄 Sync Data', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if not summary_df.empty:
    # Use tabs for navigation
    tab1, tab2, tab3 = st.tabs(["📅 Training Log", "🔍 Activity Details", "📈 Global Trends"])

    # --- TAB 1: CALENDAR ---
    with tab1:
        st.components.v1.html(generate_calendar_html(summary_df), height=600, scrolling=True)

    # --- TAB 2: ACTIVITY DETAILS ---
    with tab2:
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity to inspect:", list(options.keys()))
        run_stats = summary_df[summary_df['id'] == options[selection]].iloc[0]
        
        # --- TOP METRICS (Now 4 Columns) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{run_stats['distance_km']:.2f} km")
        m2.metric("Time", f"{run_stats['moving_time_min']:.1f} min")
        m3.metric("Avg Pace", f"{format_pace(run_stats['avg_pace'])} /km")
        elev_gain = run_stats.get('total_elevation_gain', 0)
        m4.metric("Elev Gain", f"{elev_gain:.0f} m")
        st.divider()

        run_data = get_detailed_streams(options[selection])
        if not run_data.empty:
            # Splits logic
            run_data['km_bin'] = (run_data['dist_km']).astype(int) + 1
            splits = []
            for km, group in run_data.groupby('km_bin'):
                d_diff = (group['dist_m'].max() - group['dist_m'].min()) / 1000
                t_diff = (group['time'].max() - group['time'].min()) / 60
                if d_diff > 0.05:
                    pace = t_diff / d_diff
                    splits.append({'KM': f"KM {km}", 'Pace': pace, 'Label': f"{format_pace(pace)}"})
            
            df_splits = pd.DataFrame(splits)
            fig_splits = px.bar(df_splits, x='Pace', y='KM', orientation='h', text='Label', 
                                title="Pace Splits", color_discrete_sequence=['#4DB6AC'], template="plotly_dark")
            fig_splits.update_layout(yaxis={'autorange': 'reversed'}, xaxis_title="Pace (min/km)")
            st.plotly_chart(fig_splits, use_container_width=True, config={'displayModeBar': False})
            st.divider()

            if not run_data.empty:
                st.subheader("Pace Analysis: Continuous vs Splits")
            
                # 1. Process Split Data (Kilometer Bars)
                run_data['km_bin'] = (run_data['dist_km']).astype(int)
                splits = []
                for km, group in run_data.groupby('km_bin'):
                    d_diff = group['dist_km'].max() - group['dist_km'].min()
                    t_diff = (group['time'].max() - group['time'].min()) / 60
                    if d_diff > 0.1: # ignore tiny fragments
                        pace = t_diff / d_diff
                        splits.append({'km': km, 'pace': pace, 'label': format_pace(pace)})
                
                df_splits = pd.DataFrame(splits)
            
                # 2. Clean Continuous Data (Remove stops/outliers for a cleaner graph)
                # We cap pace at 12 min/km to keep the graph readable if you stopped for a light
                clean_stream = run_data[run_data['pace_smooth'] < 12].copy()
            
                # 3. Create the Overlaid Figure
                fig = go.Figure()
            
                # Add Continuous Pace (The transparent background line)
                fig.add_trace(go.Scatter(
                    x=clean_stream['dist_km'],
                    y=clean_stream['pace_smooth'],
                    mode='lines',
                    name='Continuous Pace',
                    line=dict(color='rgba(144, 164, 174, 0.4)', width=2), # Transparent blue-grey
                    hoverinfo='skip'
                ))
            
                # Add Pace Splits (The overlaid bars)
                fig.add_trace(go.Bar(
                    x=df_splits['km'] + 0.5, # Center bars at the midpoint of each kilometer
                    y=df_splits['pace'],
                    width=0.8,
                    name='KM Split',
                    marker_color='#4DB6AC',
                    text=df_splits['label'],
                    textposition='inside',
                    insidetextanchor='start',
                    textfont=dict(size=11, color='white'),
                    hoverinfo='y'
                ))
            
                # Configure Layout
                fig.update_layout(
                    template="plotly_dark",
                    xaxis_title="Distance (km)",
                    yaxis_title="Pace (min/km)",
                    yaxis=dict(autorange='reversed'), # FAST pace at the top
                    showlegend=False,
                    height=400,
                    margin=dict(l=10, r=10, t=20, b=10),
                    # Ensure the x-axis matches your actual run distance
                    xaxis=dict(range=[0, run_stats['distance_km']])
                )
            
                # Set smart Y-axis limits based on your actual performance
                if not df_splits.empty:
                    y_top = df_splits['pace'].min() - 0.5 # 30s faster than best split
                    y_bottom = df_splits['pace'].max() + 0.5 # 30s slower than worst split
                    fig.update_yaxes(range=[y_bottom, y_top])
            
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            st.divider()
            # Intensity Zones logic
            runs_near_5k = summary_df[summary_df['distance_km'].between(4.8, 5.5)]
            if not runs_near_5k.empty:
                best_5k_pace = runs_near_5k['avg_pace'].min()
                total_seconds = best_5k_pace * 5 * 60
                b_min, b_sec = int(total_seconds // 60), int(total_seconds % 60)
                
                st.markdown(f"### Baseline Performance")
                st.markdown(f"**Reference 5K Time:** {b_min}:{b_sec:02d} | **Pace:** {format_pace(best_5k_pace)}/km")
                st.caption("Zones below are calibrated based on this benchmark.")
            else:
                st.caption("No 5K activities found. Using default baseline (6:00/km).")
                best_5k_pace = 6.0
            
            
            st.subheader("Intensity Zones")
            current_zones = calculate_pace_zones(best_5k_pace)
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
    # --- TAB 3: GLOBAL TRENDS (With Integrated Filter) ---
    with tab3:
        st.subheader("Filter Training Period")
        
        max_date = summary_df['date'].max()
        min_date = summary_df['date'].min()
        
        d1, d2 = st.columns(2)
        with d1:
            start_sel = st.date_input("Start Date", value=max_date - timedelta(days=30), 
                                      min_value=min_date, max_value=max_date, key="trend_start")
        with d2:
            end_sel = st.date_input("End Date", value=max_date, 
                                    min_value=min_date, max_value=max_date, key="trend_end")

        # Filtering logic for the graphs
        mask = (summary_df['date'] >= start_sel) & (summary_df['date'] <= end_sel)
        trend_df = summary_df.loc[mask].copy()

        if not trend_df.empty:
            st.divider()
            tm1, tm2, tm3 = st.columns(3)
            total_km = trend_df['distance_km'].sum()
            tm1.metric("Total Distance", f"{total_km:.1f} km")
            
            days_range = max(1, (end_sel - start_sel).days)
            tm2.metric("Weekly Avg", f"{(total_km / days_range * 7):.1f} km")
            tm3.metric("Avg Pace", f"{format_pace(trend_df['avg_pace'].mean())} /km")

            c1, c2 = st.columns(2)
            with c1:
                fig_m = px.bar(trend_df, x='date', y='distance_km', title="Daily Mileage", 
                               color_discrete_sequence=['#4DB6AC'], template="plotly_dark")
                fig_m.update_xaxes(fixedrange=True)
                fig_m.update_yaxes(fixedrange=True)
                st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False})
                
            with c2:
                fig_p = px.line(trend_df, x='date', y='avg_pace', title="Pace Evolution", template="plotly_dark")
                fig_p.update_traces(line_color="#90A4AE", line_width=3, mode='lines+markers')
                fig_p.update_yaxes(autorange="reversed", fixedrange=True)
                fig_p.update_xaxes(fixedrange=True)
                st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("No runs found in this date range.")

else:
    st.info("No data available. Please sync your Strava activities.")
