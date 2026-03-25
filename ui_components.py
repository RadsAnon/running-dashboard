from datetime import datetime, timedelta

def format_pace(decimal_pace):
    if decimal_pace >= 20.0 or decimal_pace <= 0: return "∞"
    minutes = int(decimal_pace)
    seconds = int((decimal_pace - minutes) * 60)
    return f"{minutes}:{seconds:02d}"

def calculate_pace_zones(best_5k_pace_min):
    tp = best_5k_pace_min * 1.05 
    # Return both the color and the calculated limit strings
    return [
        {'name': 'Z5: Anaerobic', 'min': 0.0,       'max': tp * 0.92, 'color': '#9575CD', 'range': f"< {format_pace(tp * 0.92)}"},
        {'name': 'Z4: Threshold', 'min': tp * 0.92, 'max': tp * 1.00, 'color': '#1976D2', 'range': f"{format_pace(tp * 0.92)} - {format_pace(tp * 1.00)}"},
        {'name': 'Z3: Tempo',     'min': tp * 1.00, 'max': tp * 1.08, 'color': '#00796B', 'range': f"{format_pace(tp * 1.00)} - {format_pace(tp * 1.08)}"},
        {'name': 'Z2: Aerobic',   'min': tp * 1.08, 'max': tp * 1.29, 'color': '#2E7D32', 'range': f"{format_pace(tp * 1.08)} - {format_pace(tp * 1.29)}"},
        {'name': 'Z1: Recovery',  'min': tp * 1.29, 'max': 25.0,    'color': '#455A64', 'range': f"> {format_pace(tp * 1.29)}"}
    ]

# ... rest of generate_calendar_html stays the same ...

def generate_calendar_html(summary_df):
    text_color = "#E0E0E0"
    bubble_bg = "rgba(255, 255, 255, 0.1)"
    border_color = "rgba(255, 255, 255, 0.15)"

    style = f"""
    <style>
        body {{ background-color: transparent; margin: 0; padding: 0; }}
        .cal-container {{ font-family: sans-serif; color: {text_color}; }}
        
        /* ... other styles ... */

        .cal-activity-bubble {{ 
            border-radius: 50%; /* <--- CHANGE THIS FROM 8px TO 50% */
            background: {bubble_bg};
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: {text_color}; 
            font-weight: 600; 
            border: 1px solid {border_color};
            aspect-ratio: 1 / 1; /* Ensures it stays a perfect circle */
        }}
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
