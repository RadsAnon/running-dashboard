from datetime import datetime, timedelta

def format_pace(decimal_pace):
    """Converts decimal pace (e.g., 5.5) to string (e.g., 5:30)."""
    if decimal_pace >= 20.0 or decimal_pace <= 0: 
        return "∞"
    minutes = int(decimal_pace)
    seconds = int((decimal_pace - minutes) * 60)
    return f"{minutes}:{seconds:02d}"

def calculate_pace_zones(best_5k_pace_min):
    """Calculates intensity zones based on a reference 5K pace."""
    tp = best_5k_pace_min * 1.05  # Threshold Pace
    return [
        {'name': 'Z5: Anaerobic', 'min': 0.0,       'max': tp * 0.92, 'color': '#9575CD', 'range': f"< {format_pace(tp * 0.92)}"},
        {'name': 'Z4: Threshold', 'min': tp * 0.92, 'max': tp * 1.00, 'color': '#1976D2', 'range': f"{format_pace(tp * 0.92)} - {format_pace(tp * 1.00)}"},
        {'name': 'Z3: Tempo',     'min': tp * 1.00, 'max': tp * 1.08, 'color': '#00796B', 'range': f"{format_pace(tp * 1.00)} - {format_pace(tp * 1.08)}"},
        {'name': 'Z2: Aerobic',   'min': tp * 1.08, 'max': tp * 1.29, 'color': '#2E7D32', 'range': f"{format_pace(tp * 1.14)} - {format_pace(tp * 1.29)}"},
        {'name': 'Z1: Recovery',  'min': tp * 1.29, 'max': 25.0,    'color': '#455A64', 'range': f"> {format_pace(tp * 1.29)}"}
    ]

def generate_calendar_html(summary_df):
    """Generates a ultra-compact, mobile-friendly training calendar."""
    text_color = "#E0E0E0"
    bubble_bg = "rgba(255, 255, 255, 0.1)"
    border_color = "rgba(255, 255, 255, 0.15)"

    style = f"""
    <style>
        body {{ 
            background-color: transparent; 
            margin: 0; 
            padding: 0; 
            overflow-x: hidden; 
        }}
        .cal-container {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; 
            color: {text_color}; 
            max-width: 100%;
        }}
        .cal-header {{ 
            display: grid; 
            grid-template-columns: 75px repeat(7, 1fr); 
            gap: 4px; 
            font-weight: 600; 
            color: {text_color}; 
            opacity: 0.4; 
            text-align: center; 
            margin-bottom: 12px;
            font-size: 0.65rem; 
            text-transform: uppercase;
        }}
        .cal-week {{ 
            display: grid; 
            grid-template-columns: 75px repeat(7, 1fr); 
            gap: 4px; 
            margin-bottom: 12px; 
            border-bottom: 1px solid {border_color}; 
            padding-bottom: 8px; 
            align-items: center;
        }}
        .cal-total-km {{ 
            font-size: 1.1rem; 
            font-weight: 800; 
            color: #4DB6AC; 
            margin: 2px 0;
        }}
        .cal-day-cell {{ 
            text-align: center; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            min-height: 55px;
        }}
        .cal-activity-bubble {{ 
            border-radius: 50%; 
            background: {bubble_bg};
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: {text_color}; 
            font-weight: 700; 
            border: 1px solid {border_color};
            aspect-ratio: 1 / 1;
        }}
        .week-label {{ 
            font-size: 0.55rem; 
            text-transform: uppercase; 
            color: {text_color}; 
            opacity: 0.4; 
            white-space: nowrap;
        }}
    </style>
    """
    
    html = f"<div class='cal-container'>{style}<div class='cal-header'><div>TOTAL</div>"
    for d in ["M", "T", "W", "T", "F", "S", "S"]: 
        html += f"<div>{d}</div>"
    html += "</div>"
    
    today = datetime.now()
    curr_week_start = today - timedelta(days=today.weekday())
    
    for i in range(5):
        w_start = curr_week_start - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        
        w_data = summary_df[(summary_df['date'] >= w_start.date()) & (summary_df['date'] <= w_end.date())]
        total_km = w_data['distance_km'].sum()
        
        html += f"<div class='cal-week'>"
        html += f"""
            <div style='text-align: left;'>
                <div class='week-label'>{w_start.strftime('%b %d')}</div>
                <div class='cal-total-km'>{total_km:.1f}</div>
            </div>
        """
        
        for d_offset in range(7):
            day_to_show = w_start + timedelta(days=d_offset)
            d_data = summary_df[summary_df['date'] == day_to_show.date()]
            
            html += "<div class='cal-day-cell'>"
            if not d_data.empty:
                dist = d_data.iloc[0]['distance_km']
                # Compact scaling: 28px to 55px
                size = min(28 + (dist * 2.2), 55) 
                html += f"<div class='cal-activity-bubble' style='width: {size}px; height: {size}px; font-size: {max(9, size/3.2)}px;'>{dist:.1f}</div>"
            else: 
                html += "<div style='opacity: 0.1;'>•</div>"
            html += "</div>"
        html += "</div>"
        
    return html + "</div>"
