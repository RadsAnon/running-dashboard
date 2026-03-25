import streamlit as st
import pandas as pd
import plotly.express as px
from strava_utils import load_strava_data, get_detailed_streams
from ui_components import calculate_pace_zones, generate_calendar_html

st.set_page_config(layout="wide", page_title="Training Command Center")

# Frost Palette
PRIMARY_COLOR = "#4DB6AC" # Teal
SECONDARY_COLOR = "#90A4AE" # Slate

# --- HEADER ---
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
                           color_discrete_sequence=[PRIMARY_COLOR]), use_container_width=True)
        with c2:
            fig_p = px.line(summary_df, x='date', y='avg_pace', title="Pace Evolution")
            fig_p.update_traces(line_color=SECONDARY_COLOR, line_width=3)
            fig_p.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p, use_container_width=True)

    with tab3:
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity:", list(options.keys()))
        run_stats = summary_df[summary_df['id'] == options[selection]].iloc[0]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Distance", f"{run_stats['distance_km']:.2f} km")
        m2.metric("Time", f"{run_stats['moving_time_min']:.1f} min")
        m3.metric("Pace", f"{run_stats['avg_pace']:.2f} /km")

        run_data = get_detailed_streams(options[selection])
        
        if not run_data.empty:
            st.divider()
            run_data['km_bin'] = (run_data['dist_km']).astype(int) + 1
            splits = []
            for km, group in run_data.groupby('km_bin'):
                dist = (group['dist_m'].max() - group['dist_m'].min()) / 1000
                if dist > 0.1:
                    pace = (group['time'].max() - group['time'].min()) / 60 / dist
                    splits.append({'KM': f"KM {km}", 'Pace': pace})
            
            df_splits = pd.DataFrame(splits)
            df_splits['label'] = df_splits['Pace'].apply(lambda x: f"{x:.2f}")

            fig_splits = px.bar(df_splits, x='Pace', y='KM', orientation='h', text='label', 
                                title="Pace per Kilometer", color_discrete_sequence=[PRIMARY_COLOR])
            fig_splits.update_layout(yaxis={'autorange': 'reversed'}, margin=dict(r=50), showlegend=False)
            st.plotly_chart(fig_splits, use_container_width=True)

            best_5k = summary_df[summary_df['distance_km'].between(4.9, 5.5)]['avg_pace'].min() if not summary_df.empty else 6.0
            current_zones = calculate_pace_zones(best_5k)
            run_data['zone'] = run_data['pace_smooth'].apply(lambda p: next((z['name'] for z in current_zones if z['min'] <= p < z['max']), 'Other'))
            
            zone_time = run_data.groupby('zone')['time'].count().reset_index()
            zone_time['percent'] = (zone_time['time'] / zone_time['time'].sum()) * 100
            
            fig_zones = px.bar(zone_time, x='percent', y='zone', orientation='h', title="Intensity Distribution (%)",
                               color='zone', color_discrete_map={z['name']: z['color'] for z in current_zones})
            fig_zones.update_layout(showlegend=False, xaxis_range=[0, 100])
            st.plotly_chart(fig_zones, use_container_width=True)
else:
    st.info("No activities found for 2026.")
