
import json
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIG
# ============================================================
st.set_page_config(layout="wide", page_title="🏃‍♀️ Run For Your Life")

PLAN_PATHS = [
    Path("data/training_plan.json"),
    Path("training_plan.json"),
]

LOG_PATH = Path("manual_run_log.csv")

TEAL = "#4DB6AC"
MUTED = "#90A4AE"


# ============================================================
# HELPERS
# ============================================================
def format_pace(pace_min_per_km):
    """Convert decimal min/km to M:SS format."""
    if pace_min_per_km is None or pd.isna(pace_min_per_km) or pace_min_per_km <= 0:
        return "-"
    minutes = int(pace_min_per_km)
    seconds = int(round((pace_min_per_km - minutes) * 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d}"


def parse_pace_to_decimal(pace_text):
    """Accepts '8:15' or '8.25' and returns decimal min/km."""
    if pace_text is None:
        return None

    pace_text = str(pace_text).strip()
    if pace_text == "":
        return None

    if ":" in pace_text:
        parts = pace_text.split(":")
        if len(parts) != 2:
            return None
        minutes = float(parts[0])
        seconds = float(parts[1])
        return minutes + seconds / 60.0

    return float(pace_text)


@st.cache_data
def load_training_plan():
    """Load training plan JSON into meta + DataFrame."""
    plan_path = None
    for p in PLAN_PATHS:
        if p.exists():
            plan_path = p
            break

    if plan_path is None:
        st.error(
            "Could not find training_plan.json. Put it either at "
            "`training_plan.json` or `data/training_plan.json`."
        )
        st.stop()

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    meta = plan["meta"]
    df = pd.DataFrame(plan["runs"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["week_start"] = pd.to_datetime(df["week_start"]).dt.date
    df["planned_km"] = pd.to_numeric(df["planned_km"], errors="coerce")
    df["planned_pace"] = pd.to_numeric(df["planned_pace"], errors="coerce")

    return meta, df


def empty_log_df():
    return pd.DataFrame(
        columns=[
            "run_id",
            "actual_date",
            "actual_km",
            "actual_time_min",
            "actual_pace",
            "effort",
            "notes",
            "completed",
        ]
    )


def load_log():
    """Load manual run log from CSV."""
    if not LOG_PATH.exists():
        return empty_log_df()

    df = pd.read_csv(LOG_PATH)

    required = empty_log_df().columns
    for col in required:
        if col not in df.columns:
            df[col] = None

    df = df[list(required)]
    df["actual_date"] = pd.to_datetime(df["actual_date"], errors="coerce").dt.date
    df["actual_km"] = pd.to_numeric(df["actual_km"], errors="coerce")
    df["actual_time_min"] = pd.to_numeric(df["actual_time_min"], errors="coerce")
    df["actual_pace"] = pd.to_numeric(df["actual_pace"], errors="coerce")
    df["completed"] = df["completed"].fillna(False).astype(bool)

    return df


def save_log(df):
    """Save manual run log to CSV."""
    out = df.copy()
    out["actual_date"] = out["actual_date"].astype(str)
    out.to_csv(LOG_PATH, index=False)


def merge_plan_and_log(plan_df, log_df):
    """Join planned runs to manual actuals."""
    df = plan_df.copy()

    # Keep only latest entry per run_id, in case user re-logs a run.
    if log_df is None or log_df.empty:
        log_df = empty_log_df()
    else:
        log_df = log_df.drop_duplicates(subset=["run_id"], keep="last")

    merged = df.merge(log_df, on="run_id", how="left")

    merged["completed"] = merged["completed"].fillna(False).astype(bool)
    merged["actual_km"] = pd.to_numeric(merged["actual_km"], errors="coerce")
    merged["actual_time_min"] = pd.to_numeric(merged["actual_time_min"], errors="coerce")
    merged["actual_pace"] = pd.to_numeric(merged["actual_pace"], errors="coerce")

    return merged


def current_week_from_plan(meta):
    today = date.today()
    start = date.fromisoformat(meta["start_date"])
    week = ((today - start).days // 7) + 1
    return max(1, min(int(meta["total_weeks"]), int(week)))


def get_next_due_run(matched_df):
    incomplete = matched_df[~matched_df["completed"]].copy()
    if incomplete.empty:
        return None

    today = date.today()
    future = incomplete[incomplete["date"] >= today]
    if not future.empty:
        return future.sort_values("date").iloc[0]

    return incomplete.sort_values("date").iloc[-1]


def metrics_from_data(matched_df, meta):
    today = date.today()
    due = matched_df[matched_df["date"] <= today]
    completed_due = int(due["completed"].sum()) if not due.empty else 0
    adherence = completed_due / len(due) if len(due) else 0

    total_actual_km = matched_df["actual_km"].fillna(0).sum()
    total_planned_km = matched_df["planned_km"].fillna(0).sum()

    current_week = current_week_from_plan(meta)
    current_phase = matched_df[matched_df["week"] == current_week]["phase"].iloc[0]

    race_date = date.fromisoformat(meta["race_date"])
    days_to_race = max(0, (race_date - today).days)

    return {
        "current_week": current_week,
        "current_phase": current_phase,
        "days_to_race": days_to_race,
        "adherence": adherence,
        "completed_due": completed_due,
        "due_count": len(due),
        "total_actual_km": total_actual_km,
        "total_planned_km": total_planned_km,
    }


# ============================================================
# UI STYLE
# ============================================================
st.markdown(
    """
<style>
.stApp { background-color: #0E1117; color: #FAFAFA; }
[data-testid="stMetricLabel"] { color: #90A4AE !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #4DB6AC; }
div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================
meta, plan_df = load_training_plan()

if "manual_log" not in st.session_state:
    st.session_state.manual_log = load_log()

matched_df = merge_plan_and_log(plan_df, st.session_state.manual_log)
stats = metrics_from_data(matched_df, meta)


# ============================================================
# HEADER
# ============================================================
col_title, col_actions = st.columns([4, 1])
with col_title:
    st.title("🏃‍♀️ Run For Your Life")
    st.caption(
        f"{meta['race_name']} · Race date: {meta['race_date']} · "
        f"Goal: {meta['goal_time']}"
    )

with col_actions:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.session_state.manual_log = load_log()
        st.rerun()


# ============================================================
# TABS
# ============================================================
tab_plan, tab_input, tab_log, tab_trends = st.tabs(
    ["🎯 Plan", "✍️ Manual Entry", "📋 Run Log", "📈 Trends"]
)


# ============================================================
# TAB 1: PLAN
# ============================================================
with tab_plan:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Week", f"{stats['current_week']} / {meta['total_weeks']}")
    m2.metric("Current Phase", stats["current_phase"])
    m3.metric("Days to Race", stats["days_to_race"])
    m4.metric(
        "Adherence",
        f"{stats['adherence']:.0%}",
        f"{stats['completed_due']}/{stats['due_count']} due",
    )

    st.divider()

    st.subheader("This Week")
    week_df = matched_df[matched_df["week"] == stats["current_week"]].copy()

    cols = st.columns(3)
    for col, (_, r) in zip(cols, week_df.iterrows()):
        with col:
            status = "✅" if r["completed"] else ("⏳" if r["date"] >= date.today() else "❌")
            st.markdown(f"### {status} {r['day']}")
            st.markdown(f"**{r['run_type']}** · {r['planned_km']:.1f} km")
            st.caption(r["workout_detail"])
            st.write(f"Target pace: **{r['pace_range']} /km**")

            if r["completed"]:
                st.success(
                    f"Done: {r['actual_km']:.1f} km · "
                    f"{format_pace(r['actual_pace'])}/km · "
                    f"{r['actual_time_min']:.0f} min"
                )
            else:
                st.info("Not logged yet")

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        weekly = (
            matched_df.groupby(["week", "phase"], as_index=False)
            .agg(
                planned_km=("planned_km", "sum"),
                actual_km=("actual_km", lambda s: s.fillna(0).sum()),
                completed=("completed", "sum"),
                total=("run_id", "count"),
            )
            .sort_values("week")
        )

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=weekly["week"],
                y=weekly["planned_km"],
                name="Planned",
                marker_color=MUTED,
                opacity=0.45,
            )
        )
        fig.add_trace(
            go.Bar(
                x=weekly["week"],
                y=weekly["actual_km"],
                name="Actual",
                marker_color=TEAL,
            )
        )
        fig.update_layout(
            template="plotly_dark",
            title="Weekly Volume",
            barmode="overlay",
            xaxis_title="Week",
            yaxis_title="km",
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        long_runs = matched_df[matched_df["run_type"].isin(["Long", "Race"])].copy()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=long_runs["week"],
                y=long_runs["planned_km"],
                mode="lines+markers",
                name="Planned",
                line=dict(color=MUTED, dash="dash"),
            )
        )

        actual_longs = long_runs.dropna(subset=["actual_km"])
        if not actual_longs.empty:
            fig.add_trace(
                go.Scatter(
                    x=actual_longs["week"],
                    y=actual_longs["actual_km"],
                    mode="lines+markers",
                    name="Actual",
                    line=dict(color=TEAL),
                )
            )

        fig.update_layout(
            template="plotly_dark",
            title="Long Run Progression",
            xaxis_title="Week",
            yaxis_title="km",
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.subheader("Full Plan")
    display = matched_df[
        [
            "week",
            "date",
            "day",
            "phase",
            "run_type",
            "planned_km",
            "pace_range",
            "workout_detail",
            "completed",
            "actual_km",
            "actual_pace",
            "notes",
        ]
    ].copy()
    display["actual_pace"] = display["actual_pace"].apply(format_pace)
    st.dataframe(display, use_container_width=True, hide_index=True)


# ============================================================
# TAB 2: MANUAL ENTRY
# ============================================================
with tab_input:
    st.subheader("Log a Run Manually")

    next_run = get_next_due_run(matched_df)
    current_week_runs = matched_df[matched_df["week"] == stats["current_week"]].copy()

    options_df = pd.concat(
        [
            current_week_runs,
            matched_df[~matched_df["completed"]].head(20),
            matched_df[matched_df["completed"]].tail(20),
        ]
    ).drop_duplicates(subset=["run_id"])

    def option_label(row):
        done = "✅" if row["completed"] else "⬜"
        return (
            f"{done} {row['run_id']} · W{row['week']} · {row['date']} · "
            f"{row['day']} {row['run_type']} · planned {row['planned_km']:.1f} km"
        )

    labels = [option_label(r) for _, r in options_df.iterrows()]
    default_index = 0
    if next_run is not None:
        next_ids = options_df.index[options_df["run_id"] == next_run["run_id"]].tolist()
        if next_ids:
            default_index = list(options_df.index).index(next_ids[0])

    selected_label = st.selectbox(
        "Choose the planned run to update",
        labels,
        index=default_index if labels else 0,
    )

    selected_pos = labels.index(selected_label)
    selected_run = options_df.iloc[selected_pos]

    with st.form("manual_run_entry", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)

        with c1:
            actual_date = st.date_input("Actual date", value=date.today())
            actual_km = st.number_input(
                "Distance completed (km)",
                min_value=0.0,
                value=float(selected_run["actual_km"])
                if pd.notna(selected_run.get("actual_km"))
                else float(selected_run["planned_km"]),
                step=0.1,
            )

        with c2:
            time_min = st.number_input(
                "Total moving time (minutes)",
                min_value=0.0,
                value=float(selected_run["actual_time_min"])
                if pd.notna(selected_run.get("actual_time_min"))
                else 0.0,
                step=1.0,
            )
            pace_text = st.text_input(
                "Average pace, optional",
                value=format_pace(selected_run["actual_pace"])
                if pd.notna(selected_run.get("actual_pace"))
                else "",
                placeholder="Example: 8:15",
            )

        with c3:
            effort = st.select_slider(
                "Effort",
                options=["Very easy", "Easy", "Moderate", "Hard", "Very hard"],
                value=selected_run["effort"]
                if isinstance(selected_run.get("effort"), str)
                and selected_run.get("effort") in ["Very easy", "Easy", "Moderate", "Hard", "Very hard"]
                else "Easy",
            )
            completed = st.checkbox("Mark completed", value=True)

        notes = st.text_area(
            "Notes",
            value=selected_run["notes"]
            if isinstance(selected_run.get("notes"), str)
            else "",
            placeholder="How did it feel? Weather? Injury? Fueling?",
        )

        submitted = st.form_submit_button("Save run", use_container_width=True)

    if submitted:
        try:
            pace_decimal = parse_pace_to_decimal(pace_text)

            if pace_decimal is None and actual_km > 0 and time_min > 0:
                pace_decimal = time_min / actual_km

            new_row = {
                "run_id": selected_run["run_id"],
                "actual_date": actual_date,
                "actual_km": float(actual_km),
                "actual_time_min": float(time_min),
                "actual_pace": float(pace_decimal) if pace_decimal is not None else None,
                "effort": effort,
                "notes": notes,
                "completed": bool(completed),
            }

            log_df = st.session_state.manual_log.copy()
            log_df = log_df[log_df["run_id"] != selected_run["run_id"]]
            log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)

            st.session_state.manual_log = log_df
            save_log(log_df)

            st.success("Saved run.")
            st.rerun()

        except Exception as e:
            st.error(f"Could not save run: {e}")

    st.divider()

    st.subheader("Import / Export Manual Log")

    uploaded = st.file_uploader(
        "Upload a previous manual_run_log.csv",
        type=["csv"],
    )
    if uploaded is not None:
        try:
            uploaded_df = pd.read_csv(uploaded)
            st.session_state.manual_log = uploaded_df
            save_log(uploaded_df)
            st.success("Imported manual log.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not import CSV: {e}")

    csv_bytes = st.session_state.manual_log.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download manual_run_log.csv",
        data=csv_bytes,
        file_name="manual_run_log.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "On Streamlit Cloud, saved files can disappear after redeploys or app sleep. "
        "Use the download button occasionally as a backup."
    )


# ============================================================
# TAB 3: RUN LOG
# ============================================================
with tab_log:
    st.subheader("Logged Runs")

    logged = matched_df[matched_df["completed"]].copy().sort_values("actual_date", ascending=False)

    if logged.empty:
        st.info("No runs logged yet. Use the Manual Entry tab to add your first run.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Runs Logged", len(logged))
        c2.metric("Total Distance", f"{logged['actual_km'].sum():.1f} km")
        c3.metric("Average Pace", f"{format_pace(logged['actual_pace'].mean())}/km")
        c4.metric("Average Distance", f"{logged['actual_km'].mean():.1f} km")

        show = logged[
            [
                "run_id",
                "week",
                "actual_date",
                "day",
                "run_type",
                "planned_km",
                "actual_km",
                "actual_pace",
                "actual_time_min",
                "effort",
                "notes",
            ]
        ].copy()
        show["actual_pace"] = show["actual_pace"].apply(format_pace)
        st.dataframe(show, use_container_width=True, hide_index=True)

        delete_run = st.selectbox(
            "Delete or un-complete a logged run",
            [""] + [f"{r['run_id']} · {r['actual_date']} · {r['run_type']}" for _, r in logged.iterrows()],
        )

        if delete_run and st.button("Remove selected log entry"):
            run_id_to_delete = delete_run.split(" · ")[0]
            log_df = st.session_state.manual_log.copy()
            log_df = log_df[log_df["run_id"] != run_id_to_delete]
            st.session_state.manual_log = log_df
            save_log(log_df)
            st.success(f"Removed {run_id_to_delete}.")
            st.rerun()


# ============================================================
# TAB 4: TRENDS
# ============================================================
with tab_trends:
    st.subheader("Progress Trends")

    logged = matched_df[matched_df["completed"]].copy()
    if logged.empty:
        st.info("Trends will appear after you log some runs.")
    else:
        logged = logged.sort_values("actual_date")
        logged["actual_date"] = pd.to_datetime(logged["actual_date"])
        logged["pace_label"] = logged["actual_pace"].apply(format_pace)

        c1, c2 = st.columns(2)

        with c1:
            fig = px.bar(
                logged,
                x="actual_date",
                y="actual_km",
                color="run_type",
                template="plotly_dark",
                title="Completed Distance by Run",
                labels={"actual_date": "Date", "actual_km": "km"},
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with c2:
            fig = px.line(
                logged,
                x="actual_date",
                y="actual_pace",
                markers=True,
                text="pace_label",
                template="plotly_dark",
                title="Average Pace Trend",
                labels={"actual_date": "Date", "actual_pace": "min/km"},
            )
            fig.update_traces(textposition="top center")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        weekly_actual = (
            logged.assign(week_start=logged["actual_date"].dt.to_period("W").dt.start_time)
            .groupby("week_start", as_index=False)
            .agg(total_km=("actual_km", "sum"), runs=("run_id", "count"))
        )

        fig = px.bar(
            weekly_actual,
            x="week_start",
            y="total_km",
            text="runs",
            template="plotly_dark",
            title="Actual Weekly Mileage",
            labels={"week_start": "Week", "total_km": "km"},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
