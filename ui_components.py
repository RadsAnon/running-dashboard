from datetime import datetime, timedelta

def calculate_pace_zones(best_5k_pace_min):
    tp = best_5k_pace_min * 1.05 
    return [
        {'name': 'Z1: Recovery',  'min': tp * 1.29, 'max': 20.0, 'color': '#90A4AE'},
        {'name': 'Z2: Aerobic',   'min': tp * 1.14, 'max': tp * 1.29, 'color': '#81C784'},
        {'name': 'Z3: Tempo',     'min': tp * 1.06, 'max': tp * 1.14, 'color': '#4DB6AC'},
        {'name': 'Z4: Threshold', 'min': tp * 0.99, 'max': tp * 1.06, 'color': '#64B5F6'},
        {'name': 'Z5: Anaerobic', 'min': 0.0, 'max': tp * 0.99, 'color': '#9575CD'}
    ]

def generate_calendar_html(summary_df, is_dark=True):
    # Manually define colors based on the theme since iframes can't see CSS variables
    text_color = "#E0E0E0" if is_dark else "#262730"
    bubble_bg = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.05)"
    border_color = "rgba(255, 255, 255, 0.2)" if is_dark else "rgba(0, 0, 0, 0.1)"

    style = f"""
    <style>
        .cal-container {{ font-family: sans-serif; color: {text_color}; background-color: transparent; }}
        .cal-header {{ 
            display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 10px; 
            font-weight: 600; color: {text_color}; opacity: 0.6; text-align: center; margin-bottom: 20px;
            font-size: 0.8rem; text-transform: uppercase;
        }}
        .cal-week {{ 
            display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 10px; 
            margin-bottom: 20px; border-bottom: 1px solid {border_color}; padding-bottom: 15px; align-items: center;
        }}
        .cal-total-km {{ font-size: 1.6rem; font-weight: 800; color: #4DB6AC; }}
        .cal-day-cell {{ text-align: center; display: flex; align-items: center; justify-content: center; }}
        .cal-activity-bubble {{ 
            border-radius: 10px; background: {bubble_bg};
            display: flex; align-items: center; justify-content: center; color: {text_color}; 
            font-weight: 600; border: 1px solid {border_color};
        }}
        .week-label {{ font-size: 0.7rem; text-transform: uppercase; color: {text_color}; opacity: 0.4; }}
    </style>
    """
    html = f"<div class='cal-container'>{style}<div class='cal-header'><div>WEEK VOLUME</div>"
    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]: html += f"<div>{d}</div>"
    html += "</div>"
    
    today = datetime.now()
    curr_week_start = today - timedelta(days=today.weekday())
    
    for i in range(5):
        w_start = curr_week_start - timedelta(weeks=i)
        w_data = summary_df[(summary_df['date'] >= w_start.date()) & (summary_df['date'] <= (w_start + timedelta(days=6)).date())]
        html += f"<div class='cal-week'><div><div class='week-label'>{w_start.strftime('%b %d')}</div><div class='cal-total-km'>{w_data['distance_km'].sum():.1f}</div><div class='week-label'>KM TOTAL</div></div>"
        for d_offset in range(7):
            d_data = summary_df[summary_df['date'] == (w_start + timedelta(days=d_offset)).date()]
            html += "<div class='cal-day-cell'>"
            if not d_data.empty:
                dist = d_data.iloc[0]['distance_km']
                size = min(35 + (dist * 3), 70) 
                html += f"<div class='cal-activity-bubble' style='width: {size}px; height: {size}px;'>{dist:.1f}</div>"
            else: html += "<div style='opacity: 0.2;'>•</div>"
            html += "</div>"
        html += "</div>"
    return html + "</div>"
