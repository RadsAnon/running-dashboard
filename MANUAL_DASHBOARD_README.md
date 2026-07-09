
# Manual Running Dashboard

This version removes Strava/Samsung Health completely.

It uses your existing `training_plan.json` and lets you manually log each run from the Streamlit UI.

## Files

Use:

- `streamlit_app_manual.py` as your Streamlit app.
- Your existing `training_plan.json`.
- Optional: `manual_run_log.csv`, which the app creates after you save runs.

## How to install in your repo

Option A: replace your old app

1. Rename `streamlit_app_manual.py` to `streamlit_app.py`.
2. Put `training_plan.json` either:
   - in the repo root as `training_plan.json`, or
   - inside `data/training_plan.json`.
3. Run:
   ```bash
   streamlit run streamlit_app.py
   ```

Option B: keep both apps

1. Keep the file as `streamlit_app_manual.py`.
2. Run:
   ```bash
   streamlit run streamlit_app_manual.py
   ```

## Important note for Streamlit Cloud

The app writes manual entries to `manual_run_log.csv`.

On Streamlit Cloud, local saved files can disappear after redeploys or app sleep. Use the dashboard's "Download manual_run_log.csv" button sometimes as a backup. You can re-upload it later from the Manual Entry tab.
