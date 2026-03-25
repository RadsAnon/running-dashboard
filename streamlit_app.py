import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import time
from stravalib.client import Client
from datetime import datetime, timedelta
import plotly.express as px

def get_strava_client():
    # We pull the token data from Secrets instead of 'strava_tokens.json'
    tokens = {
        "access_token": st.secrets["access_token"],
        "refresh_token": st.secrets["refresh_token"],
        "expires_at": st.secrets["expires_at"]
    }
    
    client = Client()
    # Logic to refresh stays the same, but we'll print a warning 
    # since we can't easily "write" back to secrets from the cloud.
    client.access_token = tokens["access_token"]
    return client

st.set_page_config(layout="wide", page_title="Radhika's Training Hub")

# --- 1. THE CONNECTION ENGINE ---
def get_strava_client():
    try:
        with open('strava_tokens.json', 'r') as f:
            tokens = json.load(f)
    except FileNotFoundError:
        st.error("No tokens found! Run your 'Step 1' script first.")
        st.stop()

    client = Client()
    
    # Auto-refresh if the token is old
    if time.time() > tokens['expires_at']:
        res = client.refresh_access_token(client_id=CLIENT_ID, 
                                         client_secret=CLIENT_SECRET, 
                                         refresh_token=tokens['refresh_token'])
        with open('strava_tokens.json', 'w') as f:
            json.dump(res, f)
        client.access_token = res['access_token']
    else:
        client.access_token = tokens['access_token']
        
    return client

# --- 2. DATA LOADING ---
@st.cache_data
def load_2026_data():
    client = get_strava_client()
    # Fetch all activities from Jan 1st, 2026
    activities = client.get_activities(after='2026-01-01T00:00:00Z')
    
    data = []
    for a in activities:
        if a.type not in ['Run', 'Walk']: 
            continue
            
        # Convert Duration/Timedelta to raw seconds safely
        try:
            # If it has total_seconds (timedelta), use it. 
            # If not, try to cast the object itself to float (Duration).
            seconds = a.moving_time.total_seconds() if hasattr(a.moving_time, 'total_seconds') else float(a.moving_time)
        except Exception:
            seconds = 0
            
        dist_km = float(a.distance) / 1000 if a.distance else 0
        
        # Calculate pace: (minutes) / (km)
        moving_min = seconds / 60
        pace = moving_min / dist_km if dist_km > 0 else 0
            
        data.append({
            'id': a.id,
            'name': a.name,
            'date': a.start_date_local.date(),
            'datetime': a.start_date_local,
            'distance_km': dist_km,
            'moving_time_min': moving_min,
            'avg_pace': pace
        })
    return pd.DataFrame(data).sort_values('datetime', ascending=False)

@st.cache_data
def get_detailed_streams(activity_id):
    client = get_strava_client()
    # Get the raw GPS/Pace data for the specific run
    streams = client.get_activity_streams(activity_id, types=['time', 'distance', 'altitude'], resolution='medium')
    
    df = pd.DataFrame({
        'time': streams['time'].data,
        'dist_m': streams['distance'].data,
        'ele': streams['altitude'].data if 'altitude' in streams else 0
    })
    
    # Calculate pace per point
    df['dist_km'] = df['dist_m'] / 1000
    df['time_diff'] = df['time'].diff()
    df['dist_diff'] = df['dist_m'].diff()
    
    # Pace (min/km) = (seconds/60) / (meters/1000)
    df['pace_raw'] = (df['time_diff'] / 60) / (df['dist_diff'] / 1000)
    df['pace_smooth'] = df['pace_raw'].rolling(window=15, min_periods=1).mean()
    
    return df[df['pace_raw'] < 15].copy()

# --- 3. CUSTOM CALENDAR GRAPHIC LOGIC ---
def generate_calendar_html(summary_df, start_date):
    # CSS Updated with Streamlit's native text color variable
    style = """
    <style>
        .cal-container { 
            font-family: 'Source Sans Pro', sans-serif; 
            color: var(--text-color, #fafafa); /* Fallback to off-white for dark mode */
        }
        .cal-week { 
            display: grid; 
            grid-template-columns: 120px repeat(7, 1fr); 
            gap: 10px; 
            margin-bottom: 20px; 
            border-bottom: 1px solid rgba(128, 128, 128, 0.2); 
            padding-bottom: 10px; 
        }
        .cal-header { 
            display: grid; 
            grid-template-columns: 120px repeat(7, 1fr); 
            gap: 10px; 
            font-weight: bold; 
            text-transform: uppercase; 
            margin-bottom: 10px; 
            color: #888;
            font-size: 0.8rem;
        }
        .cal-head-item { text-align: center; }
        .cal-week-summary { display: flex; flex-direction: column; justify-content: center; }
        .cal-week-date { font-size: 1rem; font-weight: bold; }
        .cal-total-dist { font-size: 0.7rem; opacity: 0.6; text-transform: uppercase; margin-top: 2px;}
        .cal-total-km { font-size: 1.3rem; font-weight: 800; color: #fc4c02; }
        .cal-day-cell { text-align: center; padding: 5px; position: relative; min-height: 80px;}
        .cal-activity-bubble { 
            display: flex; align-items: center; justify-content: center; 
            width: 42px; height: 42px; border-radius: 50%; 
            font-weight: bold; font-size: 0.95rem; color: white;
            margin: 0 auto;
        }
        .cal-activity-name { font-size: 0.7rem; opacity: 0.9; margin-top: 4px; line-height: 1.1; color: var(--text-color, white);}
        .cal-rest-label { color: rgba(128, 128, 128, 0.3); font-size: 0.8rem; margin-top: 20px; }
        .today-marker { color: #fc4c02; font-weight: bold; font-size: 0.65rem; margin-bottom: 1px; display: block; }
    </style>
    """
    
    html = f"<div class='cal-container'>{style}"
    
    # 1. Header Row
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    html += "<div class='cal-header'><div></div>"
    for day in day_names:
        html += f"<div class='cal-head-item'>{day}</div>"
    html += "</div>"
    
    # Logic to start at the Monday of the selected month
    first_of_month = datetime(start_date.year, start_date.month, 1)
    current_day = first_of_month - timedelta(days=first_of_month.weekday())
    
    # 2. Render 5 Weeks
    for _ in range(5):
        week_end = current_day + timedelta(days=6)
        week_data = summary_df[(summary_df['date'] >= current_day.date()) & (summary_df['date'] <= week_end.date())]
        total_dist = week_data['distance_km'].sum()
        
        html += f"<div class='cal-week'><div class='cal-week-summary'>"
        html += f"<div class='cal-week-date'>{current_day.strftime('%b %d')}</div>"
        html += f"<div class='cal-total-dist'>Total</div>"
        html += f"<div class='cal-total-km'>{total_dist:.1f}</div></div>"
        
        for _ in range(7):
            day_data = summary_df[summary_df['date'] == current_day.date()]
            is_today = current_day.date() == datetime.now().date()
            
            html += "<div class='cal-day-cell'>"
            if not day_data.empty:
                row = day_data.iloc[0]
                color = "#4caf50" if "Run" in row['name'] else "#2196f3"
                
                if is_today: html += "<span class='today-marker'>TODAY</span>"
                html += f"<div class='cal-activity-bubble' style='background-color: {color};'>{row['distance_km']:.1f}</div>"
                html += f"<div class='cal-activity-name'>{row['name']}</div>"
                if is_today: html += "<div style='color: #fc4c02; font-size: 0.8rem;'>▲</div>"
            else:
                html += "<div class='cal-rest-label'>—</div>"
            
            html += "</div>"
            current_day += timedelta(days=1)
        html += "</div>"

    html += "</div>"
    return html



# --- 3. UI LAYOUT ---
st.title("🏃 Training Command Center")

if st.sidebar.button('🔄 Sync Strava Now'):
    st.cache_data.clear()
    st.rerun()

summary_df = load_2026_data()

if not summary_df.empty:
    tab1, tab2, tab3 = st.tabs(["Global Trends", "Individual Run Deep-Dive", "Global Calendar"])

    with tab1:
        st.subheader("Global Progress")
        col1, col2 = st.columns(2)
        
        with col1:
            fig_vol = px.bar(summary_df, x='date', y='distance_km', title="Mileage per Run", color_discrete_sequence=['#fc4c02'])
            st.plotly_chart(fig_vol, use_container_width=True)
        
        with col2:
            fig_pace_trend = px.line(summary_df, x='date', y='avg_pace', title="Average Pace Trend")
            fig_pace_trend.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_pace_trend, use_container_width=True)

    with tab2:
        # Dropdown by date
        date_labels = {f"{row['date']} - {row['name']}": row['id'] for _, row in summary_df.iterrows()}
        selected_label = st.selectbox("Select Activity", list(date_labels.keys()))
        
        df_run = get_detailed_streams(date_labels[selected_label])

        # Interactive Chart
        fig_pace = px.area(df_run, x='dist_km', y='pace_smooth', title="Live Pace Profile", color_discrete_sequence=['#fc4c02'])
        fig_pace.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_pace, use_container_width=True)

    # --- TAB 3 (New: Global Calendar Graphic) ---
# --- TAB 3 CODE ---
    with tab3:
        # 1. Month Filter Bar at the Top
        col_a, col_b = st.columns([1, 3])
        with col_a:
            # User can pick a month to view
            view_month = st.date_input("Filter Month", value=datetime.now().date())
        
        st.divider() # Visual break between filter and calendar

        # 2. Render Calendar
        cal_html = generate_calendar_html(summary_df, view_month)
        st.components.v1.html(cal_html, height=850, scrolling=True)

else:
    st.info("No activities found for 2026 yet! Go for a run?")
