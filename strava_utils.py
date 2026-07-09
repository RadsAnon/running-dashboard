import streamlit as st
import pandas as pd
import json
from stravalib.client import Client


def get_secret(creds, key_upper, key_lower=None):
    """
    Works with either Streamlit Secrets or local JSON.

    Streamlit Secrets should use:
        STRAVA_CLIENT_ID
        STRAVA_CLIENT_SECRET
        STRAVA_REFRESH_TOKEN

    Local strava_tokens.json can use either:
        client_id, client_secret, refresh_token
    or:
        STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
    """
    key_lower = key_lower or key_upper.lower()

    if key_upper in creds:
        return creds[key_upper]
    if key_lower in creds:
        return creds[key_lower]

    return None


def load_credentials():
    """
    Prefer Streamlit Secrets when deployed.
    Fall back to local strava_tokens.json when running locally.
    """
    if "STRAVA_CLIENT_ID" in st.secrets:
        return st.secrets

    try:
        with open("strava_tokens.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(
            "Credentials missing. Add Streamlit Secrets or local strava_tokens.json."
        )
        st.stop()


def get_strava_client():
    creds = load_credentials()

    client_id = get_secret(creds, "STRAVA_CLIENT_ID", "client_id")
    client_secret = get_secret(creds, "STRAVA_CLIENT_SECRET", "client_secret")
    refresh_token = get_secret(creds, "STRAVA_REFRESH_TOKEN", "refresh_token")

    if not client_id or not client_secret or not refresh_token:
        st.error(
            "Missing Strava credentials. You need STRAVA_CLIENT_ID, "
            "STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN."
        )
        st.stop()

    client = Client()

    # Always refresh the access token at startup.
    # This avoids needing to store access_token or expires_at in Streamlit Secrets.
    new_token = client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
    )

    client.access_token = new_token["access_token"]
    client.refresh_token = new_token["refresh_token"]
    client.token_expires_at = new_token["expires_at"]

    return client


@st.cache_data
def load_strava_data():
    client = get_strava_client()
    activities = client.get_activities(after="2026-01-01T00:00:00Z")

    data = []

    for a in activities:
        if a.type not in ["Run", "Walk"]:
            continue

        try:
            seconds = (
                a.moving_time.total_seconds()
                if hasattr(a.moving_time, "total_seconds")
                else float(a.moving_time)
            )
        except Exception:
            seconds = 0

        dist_km = float(a.distance) / 1000 if a.distance else 0
        moving_min = seconds / 60
        pace = moving_min / dist_km if dist_km > 0 else 0

        data.append(
            {
                "id": a.id,
                "name": a.name,
                "date": a.start_date_local.date(),
                "datetime": a.start_date_local,
                "distance_km": dist_km,
                "moving_time_min": moving_min,
                "avg_pace": pace,
                "total_elevation_gain": float(a.total_elevation_gain)
                if a.total_elevation_gain
                else 0,
            }
        )

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data).sort_values("datetime", ascending=False)


@st.cache_data
def get_detailed_streams(activity_id):
    try:
        client = get_strava_client()

        streams = client.get_activity_streams(
            activity_id,
            types=["time", "distance", "altitude"],
            resolution="medium",
        )

        if not streams or "time" not in streams or "distance" not in streams:
            return pd.DataFrame()

        df = pd.DataFrame(
            {
                "time": streams["time"].data,
                "dist_m": streams["distance"].data,
                "ele": streams["altitude"].data
                if "altitude" in streams
                else 0,
            }
        )

        df["dist_km"] = df["dist_m"] / 1000
        df["pace_raw"] = (df["time"].diff() / 60) / (
            df["dist_m"].diff() / 1000
        )
        df["pace_smooth"] = (
            df["pace_raw"].rolling(window=15, min_periods=1).mean()
        )

        return df.fillna(0)

    except Exception as e:
        st.error(f"Error fetching activity details: {e}")
        return pd.DataFrame()
