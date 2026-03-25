import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import time
from stravalib.client import Client
from datetime import datetime, timedelta

# --- 1. THE CONNECTION ENGINE ---
def get_strava_client():
    if "access_token" in st.secrets:
        client_id = st.secrets["client_id"]
        client_secret = st.secrets["client_secret"]
        access_token = st.secrets["access_token"]
        refresh_token = st.secrets["refresh_token"]
        expires_at = st.secrets["expires_at"]
    else:
        try:
            with open('strava_tokens.json', 'r') as f:
                res = json.load(f)
                client_id = res['client_id']
                client_secret = res['client_secret']
                access_token = res['access_token']
                refresh_token = res['refresh_token']
                expires_at = res['expires_at']
        except FileNotFoundError:
            st.error("Credentials missing. Add to Secrets or local JSON.")
            st.stop()

    client = Client()
    client.access_token = access_token
    client.refresh_token = refresh_token
    client.token_expires_at = expires_at

    if time.time() > expires_at:
        new_token = client.refresh_access_token(
            client_id=client_id, client_secret=client_secret, refresh_token=refresh_token
        )
        client.access_token = new_token['access_token']
    return client

st.set_page_config(layout="wide", page_title="Training Command Center")

# --- 2. DATA LOADING ---
@st.cache_data
def load_2026_data():
    client = get_strava_client()
    activities = client.get_activities(after='2026-01-01T00:00:00Z')
    data = []
    for a in activities:
        if a.type not in ['Run', 'Walk']: continue
        try:
            seconds = a.moving_time.total_seconds() if hasattr(a.moving_time, 'total_seconds') else float(a.moving_time)
        except: seconds = 0
        dist_km = float(a.distance) / 1000 if a.distance else 0
        moving_min = seconds / 60
        pace = moving_min / dist_km if dist_km > 0 else 0
        data.append({
            'id': a.id, 'name': a.name, 'date': a.start_date_local.date(),
            'datetime': a.start_date_local, 'distance_km': dist_km,
            'moving_time_min': moving_min, 'avg_pace': pace
        })
    return pd.DataFrame(data).sort_values('datetime', ascending=False)

# --- 3. DYNAMIC TRAINING LOG (CALENDAR) ---
def generate_calendar_html(summary_df):
    style = """
    <style>
        .cal-container { font-family: sans-serif; color: var(--text-color, #eee); }
        .cal-header { display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 10px; font-weight: bold; color: #888; text-align: center; margin-bottom: 20px;}
        .cal-week { display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 10px; margin-bottom: 25px; border-bottom: 1px solid rgba(128,128,128,0.1); padding-bottom: 20px; align-items: center;}
        .cal-total-km { font-size: 1.8rem; font-weight: 900; color: #fc4c02; }
        .cal-day-cell { text-align: center; min-height: 100px; display: flex; align-items: center; justify-content: center; }
        .cal-activity-bubble { 
            border-radius: 50%; background: linear-gradient(135deg, #fc4c02 0%, #ff7a45 100%);
            display: flex; align-items: center; justify-content: center; color: white; font-weight: 800;
            box-shadow: 0 4px 12px rgba(252, 76, 2, 0.4); border: 2px solid rgba(255,255,255,0.2);
        }
        .week-label { font-size: 0.7rem; text-transform: uppercase; color: #666; letter-spacing: 1px; }
    </style>
    """
    html = f"<div class='cal-container'>{style}<div class='cal-header'><div>WEEK VOLUME</div>"
    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]: html += f"<div>{d}</div>"
    html += "</div>"
    
    # Start from current week Monday
    today = datetime.now()
    curr_week_start = today - timedelta(days=today.weekday())
    
    # Render 5 weeks ANTI-CHRONOLOGICALLY (latest first)
    for i in range(5):
        w_start = curr_week_start - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        w_data = summary_df[(summary_df['date'] >= w_start.date()) & (summary_df['date'] <= w_end.date())]
        
        html += f"<div class='cal-week'><div><div class='week-label'>{w_start.strftime('%b %d')}</div><div class='cal-total-km'>{w_data['distance_km'].sum():.1f}</div><div class='week-label'>KM TOTAL</div></div>"
        
        for d_offset in range(7):
            day_to_show = w_start + timedelta(days=d_offset)
            d_data = summary_df[summary_df['date'] == day_to_show.date()]
            html += "<div class='cal-day-cell'>"
            if not d_data.empty:
                dist = d_data.iloc[0]['distance_km']
                # PROMINENT SIZING: Base 40 + 5 per km
                size = min(20 + (dist * 5), 100) 
                html += f"<div class='cal-activity-bubble' style='width: {size}px; height: {size}px; font-size: {max(0.8, size/70)}rem;'>{dist:.1f}</div>"
            else: html += "<div style='color:#333; font-size:1.5rem;'>•</div>"
            html += "</div>"
        html += "</div>"
    return html + "</div>"

# --- 4. HEADER LAYOUT (TOP RIGHT BUTTON) ---
col_title, col_sync = st.columns([4, 1])

with col_title:
    st.title("🏃 Training Command Center")

with col_sync:
    # Placing button in the right-most column
    if st.button('🔄 Sync Data', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

@st.cache_data
def get_detailed_streams(activity_id):
    try:
        client = get_strava_client()
        # Fetching the raw GPS/Time data from Strava
        streams = client.get_activity_streams(activity_id, types=['time', 'distance', 'altitude'], resolution='medium')
        
        if not streams or 'time' not in streams:
            return pd.DataFrame()

        df = pd.DataFrame({
            'time': streams['time'].data, 
            'dist_m': streams['distance'].data,
            'ele': streams['altitude'].data if 'altitude' in streams else 0
        })
        
        df['dist_km'] = df['dist_m'] / 1000
        # Calculate pace smoothing for the 'Live Profile' chart
        df['pace_raw'] = (df['time'].diff() / 60) / (df['dist_m'].diff() / 1000)
        df['pace_smooth'] = df['pace_raw'].rolling(window=15, min_periods=1).mean()
        
        return df.fillna(0)
    except Exception as e:
        st.error(f"Error fetching activity details: {e}")
        return pd.DataFrame()

# --- 5. MAIN TABS ---
summary_df = load_2026_data()

if not summary_df.empty:
    tab1, tab2, tab3 = st.tabs(["📅 Training Log", "📈 Global Trends", "🔍 Activity Details"])

    with tab1:
        # Latest week is now at the top automatically
        st.components.v1.html(generate_calendar_html(summary_df), height=800, scrolling=True)

    with tab2:
        st.subheader("2026 Performance Trends")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(summary_df, x='date', y='distance_km', title="Daily Mileage", color_discrete_sequence=['#fc4c02']), use_container_width=True)
        with c2:
            fig_p = px.line(summary_df, x='date', y='avg_pace', title="Pace Evolution")
            fig_p.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p, use_container_width=True)

    with tab3:
        # 1. Activity Selector
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity to analyze:", list(options.keys()))
        
        # 2. Key Metrics Header
        run_stats = summary_df[summary_df['id'] == options[selection]].iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Distance", f"{run_stats['distance_km']:.2f} km")
        m2.metric("Moving Time", f"{run_stats['moving_time_min']:.1f} min")
        m3.metric("Avg Pace", f"{run_stats['avg_pace']:.2f} min/km")

        st.divider()

        # 3. KM Splits Calculation
        # We use the detailed streams to find the time at each kilometer mark
        run_data = get_detailed_streams(options[selection])
        
        # Create 'KM' bins
        run_data['km_bin'] = (run_data['dist_km']).astype(int) + 1
        
        # Group by bin to find the time taken for each specific KM
        splits = []
        # Only keep splits that have a meaningful amount of data
        for km, group in run_data.groupby('km_bin'):
            dist_in_km = (group['dist_m'].max() - group['dist_m'].min()) / 1000
            if dist_in_km > 0.1: # Only count if the split is at least 100m
                time_taken = group['time'].max() - group['time'].min()
                pace_min = time_taken / 60 / dist_in_km
                splits.append({'KM': f"KM {km}", 'Pace': pace_min})
        
        df_splits = pd.DataFrame(splits)

        # 4. Horizontal Bar Graph: Pace Splits
        if not df_splits.empty:
            st.subheader("Split Analysis")
            
            # Use orientation='h' for horizontal bars
            fig_splits = px.bar(
                df_splits, 
                x='Pace', 
                y='KM', 
                orientation='h',
                title="Pace per Kilometer",
                labels={'Pace': 'Pace (min/km)', 'KM': 'Split'},
                color='Pace',
                color_continuous_scale='OrRd' # Colors get darker/redder as pace gets slower
            )
            
            # Standard running charts invert the X-axis for pace so 'faster' is further right,
            # but for a bar graph, it's often more intuitive to keep 0 on the left.
            # We will sort Y-axis to keep KM 1 at the top.
            fig_splits.update_layout(yaxis={'categoryorder':'descending'}, showlegend=False)
            
            st.plotly_chart(fig_splits, use_container_width=True)

        # 5. Continuous Pace Profile (The area chart you had before)
        st.subheader("Live Pace Profile")
        f_pace = px.area(run_data, x='dist_km', y='pace_smooth', title="Continuous Pace (min/km)", color_discrete_sequence=['#fc4c02'])
        f_pace.update_yaxes(autorange="reversed") # Invert so "faster" (lower number) is higher up
        st.plotly_chart(f_pace, use_container_width=True)

else:
    st.info("No activities found for 2026. Time for a run?")
