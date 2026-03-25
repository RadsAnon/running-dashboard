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

