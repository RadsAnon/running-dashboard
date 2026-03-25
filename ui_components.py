from datetime import datetime, timedelta
import pandas as pd

def calculate_pace_zones(best_5k_pace_min):
    threshold_pace = best_5k_pace_min * 1.05 
    return [
        {'name': 'Z1: Recovery',  'min': threshold_pace * 1.29, 'max': 20.0, 'color': '#d1d1d1'},
        {'name': 'Z2: Aerobic',   'min': threshold_pace * 1.14, 'max': threshold_pace * 1.29, 'color': '#2eb82e'},
        {'name': 'Z3: Tempo',     'min': threshold_pace * 1.06, 'max': threshold_pace * 1.14, 'color': '#ffcc00'},
        {'name': 'Z4: Threshold', 'min': threshold_pace * 0.99, 'max': threshold_pace * 1.06, 'color': '#ff8000'},
        {'name': 'Z5: Anaerobic', 'min': 0.0, 'max': threshold_pace * 0.99, 'color': '#ff3300'}
    ]

def generate_calendar_html(summary_df):
    # ... (Keep your existing CSS and HTML generation code here) ...
    # Make sure to return the full HTML string
    return html_string
