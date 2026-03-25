from datetime import datetime, timedelta

def calculate_pace_zones(best_5k_pace_min):
    tp = best_5k_pace_min * 1.05 
    return [
        {'name': 'Z1: Recovery',  'min': tp * 1.29, 'max': 20.0, 'color': '#90A4AE'}, # Muted Slate
        {'name': 'Z2: Aerobic',   'min': tp * 1.14, 'max': tp * 1.29, 'color': '#81C784'}, # Sage Green
        {'name': 'Z3: Tempo',     'min': tp * 1.06, 'max': tp * 1.14, 'color': '#4DB6AC'}, # Muted Teal
        {'name': 'Z4: Threshold', 'min': tp * 0.99, 'max': tp * 1.06, 'color': '#64B5F6'}, # Sky Blue
        {'name': 'Z5: Anaerobic', 'min': 0.0, 'max': tp * 0.99, 'color': '#9575CD'}  # Muted Purple
    ]

def generate_calendar_html(summary_df):
    # Fixed: Headers now use var(--text-color) and opacity for adaptive styling
    style = """
    <style>
        .cal-container { 
            font-family: 'Source Sans Pro', sans-serif; 
            color: var(--text-color); 
            background-color: transparent;
        }
        .cal-header { 
            display: grid; 
            grid-template-columns: 140px repeat(7, 1fr); 
            gap: 10px; 
            font-weight: 600; 
            color: var(--text-color);
            opacity: 0.7; 
            text-align: center; 
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 0.05rem;
            font-size: 0.85rem;
        }
        .cal-week { 
            display: grid; 
            grid-template-columns: 140px repeat(7, 1fr); 
            gap: 10px; 
            margin-bottom: 25px; 
            border-bottom: 1px solid rgba(128,128,128,0.2); 
            padding-bottom: 20px; 
            align-items: center;
        }
        .cal-total-km { 
            font-size: 1.8rem; 
            font-weight: 800; 
            color: #4DB6AC; /* Keeping the teal brand color for totals */
        }
        .cal-day-cell { 
            text-align: center; 
            min-height: 80px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .cal-activity-bubble { 
            border-radius: 12px; 
            background: rgba(128, 128, 128, 0.2); /* Semi-transparent adapts to BG */
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: var(--text-color); 
            font-weight: 600;
            border: 1px solid rgba(128,128,128,0.3);
        }
        .week-label { 
            font-size: 0.75rem; 
            text-transform: uppercase; 
            color: var(--text-color);
            opacity: 0.5; 
        }
    </style>
    """
    html = f"<div class='cal-container'>{style}<div class='cal-header'><div>WEEK VOLUME</div>"
    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]: 
        html += f"<div>{d}</div>"
    html += "</div>"
    
    today = datetime.now()
    curr_week_start = today - timedelta(days=today.weekday())
    
    for i in range(5):
        w_start = curr_week_start - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        w_data = summary_df[(summary_df['date'] >= w_start.date()) & (summary_df['date'] <= w_end.date())]
        
        html += f"<div class='cal-week'>"
        html += f"<div><div class='week-label'>{w_start.strftime('%b %d')}</div><div class='cal-total-km'>{w_data['distance_km'].sum():.1f}</div><div class='week-label'>KM TOTAL</div></div>"
        
        for d_offset in range(7):
            day_to_show = w_start + timedelta(days=d_offset)
            d_data = summary_df[summary_df['date'] == day_to_show.date()]
            html += "<div class='cal-day-cell'>"
            if not d_data.empty:
                dist = d_data.iloc[0]['distance_km']
                # Scale size based on distance
                size = min(35 + (dist * 3), 75) 
                html += f"<div class='cal-activity-bubble' style='width: {size}px; height: {size}px;'>{dist:.1f}</div>"
            else: 
                html += "<div style='opacity: 0.2; color: var(--text-color);'>•</div>"
            html += "</div>"
        html += "</div>"
    
    return html + "</div>"
