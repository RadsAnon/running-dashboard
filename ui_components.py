from datetime import datetime, timedelta
import pandas as pd

def calculate_pace_zones(best_5k_pace_min):
    threshold_pace = best_5k_pace_min * 1.05 
    return [
        {'name': 'Z1: Recovery',  'min': threshold_pace * 1.29, 'max': 20.0, 'color': '#455A64'}, # Blue-Grey
        {'name': 'Z2: Aerobic',   'min': threshold_pace * 1.14, 'max': threshold_pace * 1.29, 'color': '#2E7D32'}, # Deep Green
        {'name': 'Z3: Tempo',     'min': threshold_pace * 1.06, 'max': threshold_pace * 1.14, 'color': '#F9A825'}, # Amber/Gold
        {'name': 'Z4: Threshold', 'min': threshold_pace * 0.99, 'max': threshold_pace * 1.06, 'color': '#EF6C00'}, # Muted Orange
        {'name': 'Z5: Anaerobic', 'min': 0.0, 'max': threshold_pace * 0.99, 'color': '#C62828'}  # Deep Oxide Red
    ]

def generate_calendar_html(summary_df):
    # Matches the "Dark Mode" aesthetic with lower brightness bubbles
    style = """
    <style>
        .cal-container { font-family: 'Inter', sans-serif; color: #E0E0E0; background-color: #0E1117; }
        .cal-header { display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 10px; font-weight: 600; color: #616161; text-align: center; margin-bottom: 20px;}
        .cal-week { display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 10px; margin-bottom: 25px; border-bottom: 1px solid #262730; padding-bottom: 20px; align-items: center;}
        .cal-total-km { font-size: 1.8rem; font-weight: 800; color: #D84315; }
        .cal-day-cell { text-align: center; min-height: 80px; display: flex; align-items: center; justify-content: center; }
        .cal-activity-bubble { 
            border-radius: 50%; background: linear-gradient(135deg, #BF360C 0%, #E64A19 100%);
            display: flex; align-items: center; justify-content: center; color: white; font-weight: 700;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
        }
        .week-label { font-size: 0.7rem; text-transform: uppercase; color: #757575; }
    </style>
    """
    html = f"<div class='cal-container'>{style}<div class='cal-header'><div>WEEK VOLUME</div>"
    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]: html += f"<div>{d}</div>"
    html += "</div>"
    
    today = datetime.now()
    curr_week_start = today - timedelta(days=today.weekday())
    
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
                size = min(35 + (dist * 4), 85) 
                html += f"<div class='cal-activity-bubble' style='width: {size}px; height: {size}px;'>{dist:.1f}</div>"
            else: html += "<div style='color:#333;'>•</div>"
            html += "</div>"
        html += "</div>"
    return html + "</div>"
