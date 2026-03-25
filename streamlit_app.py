import streamlit as st
import pandas as pd
import plotly.express as px
from strava_utils import load_strava_data, get_detailed_streams
from ui_components import calculate_pace_zones, generate_calendar_html

st.set_page_config(layout="wide", page_title="Training Command Center")

# Force Dark Mode CSS
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        [data-testid="stMetricLabel"] { color: #90A4AE !important; }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stWidgetLabel"] p { color: #FAFAFA; }
        .stTable { background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

summary_df = load_strava_data()

if not summary_df.empty:
    tab1, tab2, tab3 = st.tabs(["📅 Training Log", "📈 Global Trends", "🔍 Activity Details"])

    with tab1:
        st.components.v1.html(generate_calendar_html(summary_df), height=650, scrolling=True)

    with tab3:
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity:", list(options.keys()))
        run_stats = summary_df[summary_df['id'] == options[selection]].iloc[0]
        
        # Calculate Zones once
        runs_near_5k = summary_df[summary_df['distance_km'].between(4.8, 5.5)]
        best_5k = runs_near_5k['avg_pace'].min() if not runs_near_5k.empty else 6.0
        current_zones = calculate_pace_zones(best_5k)

        # --- NEW: ZONE LEGEND TABLE ---
        st.subheader("Target Intensity Reference")
        legend_data = [{"Zone": z['name'], "Pace Range (min/km)": z['range']} for z in current_zones]
        st.table(pd.DataFrame(legend_data))

        run_data = get_detailed_streams(options[selection])
        if not run_data.empty:
            st.divider()
            
            # --- SPLITS ---
            run_data['km_bin'] = (run_data['dist_km']).astype(int) + 1
            splits = []
            for km, group in run_data.groupby('km_bin'):
                d_diff = (group['dist_m'].max() - group['dist_m'].min()) / 1000
                t_diff = (group['time'].max() - group['time'].min()) / 60
                if d_diff > 0.1:
                    pace = t_diff / d_diff
                    splits.append({'KM': f"KM {km}", 'Pace': pace, 'Label': f"{pace:.2f}"})
            
            df_splits = pd.DataFrame(splits)
            fig_splits = px.bar(df_splits, x='Pace', y='KM', orientation='h', text='Label', 
                                title="Pace Splits", color_discrete_sequence=['#4DB6AC'], template="plotly_dark")
            fig_splits.update_traces(textposition='outside')
            fig_splits.update_layout(yaxis={'autorange': 'reversed'})
            st.plotly_chart(fig_splits, use_container_width=True)

            # --- ZONES CHART ---
            def get_zone(p):
                for z in current_zones:
                    if z['min'] <= p < z['max']: return z['name']
                return 'Other'

            run_data['zone'] = run_data['pace_smooth'].apply(get_zone)
            zone_time = run_data.groupby('zone')['time'].count().reset_index()
            zone_time['percent'] = (zone_time['time'] / zone_time['time'].sum()) * 100
            
            z_order = [z['name'] for z in reversed(current_zones)]
            zone_time['zone'] = pd.Categorical(zone_time['zone'], categories=z_order, ordered=True)
            zone_time = zone_time.sort_values('zone')

            fig_zones = px.bar(zone_time, x='percent', y='zone', orientation='h', title="Time in Zone (%)",
                               color='zone', color_discrete_map={z['name']: z['color'] for z in current_zones}, template="plotly_dark")
            st.plotly_chart(fig_zones, use_container_width=True)

else:
    st.info("No activities found for 2026.")
