import streamlit as st
import pandas as pd
import time
import json
from stravalib.client import Client

def get_strava_client():
    if "access_token" in st.secrets:
        creds = st.secrets
    else:
        try:
            with open('strava_tokens.json', 'r') as f:
                creds = json.load(f)
        except FileNotFoundError:
            st.error("Credentials missing. Add to Secrets or local strava_tokens.json.")
            st.stop()

    client = Client()
    client.access_token = creds['access_token']
    client.refresh_token = creds['refresh_token']
    client.token_expires_at = creds['expires_at']

    if time.time() > creds['expires_at']:
        new_token = client.refresh_access_token(
            client_id=creds['client_id'], 
            client_secret=creds['client_secret'], 
            refresh_token=creds['refresh_token']
        )
        client.access_token = new_token['access_token']
    return client

@st.cache_data
def load_strava_data():
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
    try:
        client = get_strava_client()
        streams = client.get_activity_streams(activity_id, types=['time', 'distance', 'altitude'], resolution='medium')
        if not streams or 'time' not in streams: return pd.DataFrame()

        df = pd.DataFrame({
            'time': streams['time'].data, 
            'dist_m': streams['distance'].data,
            'ele': streams['altitude'].data if 'altitude' in streams else 0
        })
        df['dist_km'] = df['dist_m'] / 1000
        df['pace_raw'] = (df['time'].diff() / 60) / (df['dist_m'].diff() / 1000)
        df['pace_smooth'] = df['pace_raw'].rolling(window=15, min_periods=1).mean()
        return df.fillna(0)
    except Exception as e:
        st.error(f"Error fetching activity details: {e}")
        return pd.DataFrame()
