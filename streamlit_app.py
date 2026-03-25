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
        # Cloud Mode
        client_id = st.secrets["client_id"]
        client_secret = st.secrets["client_secret"]
        access_token = st.secrets["access_token"]
        refresh_token = st.secrets["refresh_token"]
        expires_at = st.secrets["expires_at"]
    else:
        # Local Laptop Mode
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

st.set_page_config(layout="wide", page_title="Radhika's Training Hub")

# --- 2. DATA LOADING & CACHING ---
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

@st.cache_data
def get_detailed_streams(activity_id):
    client = get_strava_client()
    streams = client.get_activity_streams(activity_id, types=['time', 'distance', 'altitude'], resolution='medium')
    df = pd.DataFrame({
        'time': streams['time'].data, 'dist_m': streams['distance'].data,
        'ele': streams['altitude'].data if 'altitude' in streams else 0
    })
    df['dist_km'] = df['dist_m'] / 1000
    df['pace_raw'] = (df['time'].diff() / 60) / (df['dist_m'].diff() / 1000)
    df['pace_smooth'] = df['pace_raw'].rolling(window=15, min_periods=1).mean()
    return df[df['pace_raw'] < 15].copy()

# --- 3. CALENDAR GENERATOR ---
def generate_calendar_html(summary_df, start_date):
    style = """
    <style>
        .cal-container { font-family: sans-serif; color: var(--text-color, #eee); }
        .cal-header { display: grid; grid-template-columns: 120px repeat(7, 1fr); gap: 10px; font-weight: bold; color: #888; margin-bottom: 10px; text-align: center;}
        .cal-week { display: grid; grid-template-columns: 120px repeat(7, 1fr); gap: 10px; margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px;}
        .cal-total-km { font-size: 1.4rem; font-weight: 800; color: #fc4c02; }
        .cal-day-cell { text-align: center; min-height: 80px; display: flex; align-items: center; justify-content: center; position: relative; }
        .cal-activity-bubble { 
            border-radius: 50%; 
            background: #fc4c02; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: white; 
            font-weight: bold; 
            transition: transform 0.2s;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        .cal-rest { color: #444; font-size: 1.2rem; }
    </style>
    """
    html = f"<div class='cal-container'>{style}<div class='cal-header'><div>Week Of</div>"
    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]: html += f"<div>{d}</div>"
    html += "</div>"
    
    first_of_month = datetime(start_date.year, start_date.month, 1)
    curr = first_of_month - timedelta(days=first_of_month.weekday())
    
    for _ in range(5):
        w_end = curr + timedelta(days=6)
        w_data = summary_df[(summary_df['date'] >= curr.date()) & (summary_df['date'] <= w_end.date())]
        html += f"<div class='cal-week'><div><div style='font-size:0.8rem'>{curr.strftime('%b %d')}</div><div class='cal-total-km'>{w_data['distance_km'].sum():.1f}k</div></div>"
        
        for _ in range(7):
            d_data = summary_df[summary_df['date'] == curr.date()]
            html += "<div class='cal-day-cell'>"
            
            if not d_data.empty:
                dist = d_data.iloc[0]['distance_km']
                # --- DYNAMIC SIZING LOGIC ---
                # Base size is 30px. We add 3px for every km run. 
                # A 5k = 45px circle. A 15k = 75px circle.
                size = 30 + (dist * 3) 
                # Cap the size so it doesn't break the grid on massive runs
                size = min(size, 85) 
                
                html += f"<div class='cal-activity-bubble' style='width: {size}px; height: {size}px; font-size: {max(0.7, size/60)}rem;'>{dist:.1f}</div>"
            else: 
                html += "<div class='cal-rest'>—</div>"
            
            html += "</div>"
            curr += timedelta(days=1)
        html += "</div>"
    return html + "</div>"

# --- 4. MAIN UI ---
st.title("🏃 Radhika's Training Command Center")

if st.sidebar.button('🔄 Sync Data'):
    st.cache_data.clear()
    st.rerun()

summary_df = load_2026_data()

if not summary_df.empty:
    # UPDATED TAB ORDER
    tab1, tab2, tab3 = st.tabs(["📅 Training Log", "📈 Global Trends", "🔍 Activity Details"])

    with tab1:
        col_f, _ = st.columns([1, 2])
        view_month = col_f.date_input("Filter Month", value=datetime.now().date())
        st.components.v1.html(generate_calendar_html(summary_df, view_month), height=600)

    with tab2:
        st.subheader("2026 Performance Trends")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(summary_df, x='date', y='distance_km', title="Daily Mileage", color_discrete_sequence=['#fc4c02']), use_container_width=True)
        with c2:
            fig_p = px.line(summary_df, x='date', y='avg_pace', title="Pace Evolution")
            fig_p.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p, use_container_width=True)
        
        # Monthly Totals
        summary_df['month'] = pd.to_datetime(summary_df['date']).dt.strftime('%B')
        monthly = summary_df.groupby('month')['distance_km'].sum().reset_index()
        st.plotly_chart(px.area(monthly, x='month', y='distance_km', title="Total Monthly Volume"), use_container_width=True)

    with tab3:
        options = {f"{r['date']} - {r['name']}": r['id'] for _, r in summary_df.iterrows()}
        selection = st.selectbox("Pick an activity to analyze:", list(options.keys()))
        
        run_data = get_detailed_streams(options[selection])
        f_pace = px.area(run_data, x='dist_km', y='pace_smooth', title="Pace Profile (min/km)", color_discrete_sequence=['#fc4c02'])
        f_pace.update_yaxes(autorange="reversed")
        st.plotly_chart(f_pace, use_container_width=True)
        
        # Stats summary for the individual run
        run_stats = summary_df[summary_df['id'] == options[selection]].iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Distance", f"{run_stats['distance_km']:.2f} km")
        m2.metric("Duration", f"{run_stats['moving_time_min']:.1f} min")
        m3.metric("Avg Pace", f"{run_stats['avg_pace']:.2f} min/km")

else:
    st.info("No activities found for 2026. Time for a run?")
