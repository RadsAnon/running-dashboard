"""Generate data/training_plan.json from the plan structure.

Run this once to produce the JSON. Edit the PLAN list below to change
distances/paces, then re-run to regenerate.
"""
import json
from datetime import date, timedelta

# ------------------------------------------------------------------
# CONFIG - edit these to customize
# ------------------------------------------------------------------
START_DATE = date(2026, 7, 13)   # Monday of Week 1
RACE_DATE  = date(2027, 2, 7)    # Sunday of Week 30
RACE_NAME  = "Half Marathon"
GOAL_TIME  = "1:45-1:50"
BASELINE_5K_PACE_MIN = 7.0        # min/km - user's current 5K pace

# Pace targets (decimal minutes per km) - stored as midpoint of each range
PACE_EASY  = 8.25   # 8:15
PACE_LONG  = 8.375  # 8:22
PACE_TEMPO = 7.375  # 7:22
PACE_HM    = 7.667  # 7:40
PACE_RACE  = 7.667

PACE_RANGE_EASY  = "8:00-8:30"
PACE_RANGE_LONG  = "8:00-8:45"
PACE_RANGE_TEMPO = "7:15-7:30"
PACE_RANGE_HM    = "7:30-7:50"

# ------------------------------------------------------------------
# The 30-week plan
# Format: (week, phase, focus, easy_km, quality_km, quality_detail, long_km, long_detail, cutback)
# ------------------------------------------------------------------
PLAN = [
    (1,  "Base", "Getting started",  5, 5, "Easy conversational pace",                                8,   "Easy pace, keep it conversational",                     False),
    (2,  "Base", "Build routine",    5, 6, "Easy conversational pace",                                9,   "Easy pace",                                              False),
    (3,  "Base", "Build volume",     6, 6, "Easy conversational pace",                                10,  "Easy pace",                                              False),
    (4,  "Base", "CUTBACK week",     5, 5, "Easy conversational pace",                                8,   "Easy pace - recovery week",                              True),
    (5,  "Base", "Add pickups",      6, 6, "Warm up, then 4x2 min at tempo pace w/ 2 min jog",        11,  "Easy pace",                                              False),
    (6,  "Base", "Build pickups",    6, 7, "Warm up, then 4x2 min at tempo pace w/ 2 min jog",        12,  "Easy pace",                                              False),
    (7,  "Base", "Peak base",        7, 7, "Warm up, then 5x2 min at tempo pace w/ 2 min jog",        13,  "Easy pace",                                              False),
    (8,  "Base", "CUTBACK week",     5, 6, "Easy conversational pace",                                10,  "Easy pace - recovery week",                              True),
    (9,  "Endurance", "Intro tempo",     6, 6, "2km easy + 10 min tempo + 2km easy",                  13,  "Easy pace",                                              False),
    (10, "Endurance", "Build tempo",     6, 7, "2km easy + 15 min tempo + 2km easy",                  14,  "Easy pace",                                              False),
    (11, "Endurance", "Extend tempo",    7, 7, "2km easy + 20 min tempo + 2km easy",                  15,  "Easy pace",                                              False),
    (12, "Endurance", "CUTBACK week",    5, 6, "2km easy + 15 min tempo + 2km easy",                  11,  "Easy pace - recovery week",                              True),
    (13, "Endurance", "Solid tempo",     7, 7, "2km easy + 20 min tempo + 2km easy",                  15,  "Easy, last 2km at HM goal pace",                         False),
    (14, "Endurance", "Extend tempo",    7, 8, "2km easy + 25 min tempo + 2km easy",                  16,  "Easy, last 2km at HM goal pace",                         False),
    (15, "Endurance", "Peak endurance",  7, 8, "2km easy + 25 min tempo + 2km easy",                  17,  "Easy, last 3km at HM goal pace",                         False),
    (16, "Endurance", "CUTBACK week",    6, 6, "2km easy + 15 min tempo + 2km easy",                  13,  "Easy pace - recovery week",                              True),
    (17, "Race-Specific", "Intro intervals", 6, 8, "2km wu + 4x1km at tempo w/ 90s jog + 2km cd",     15,  "Easy pace",                                              False),
    (18, "Race-Specific", "HM pace work",    7, 8, "2km wu + 4km at HM goal pace + 2km cd",           16,  "Easy, last 3km at HM goal pace",                         False),
    (19, "Race-Specific", "Intervals",       7, 8, "2km wu + 5x1km at tempo w/ 90s jog + 1km cd",     17,  "Easy pace",                                              False),
    (20, "Race-Specific", "CUTBACK week",    6, 6, "Easy conversational pace",                        13,  "Easy pace - recovery week",                              True),
    (21, "Race-Specific", "HM pace work",    7, 9, "2km wu + 5km at HM goal pace + 2km cd",           18,  "Easy, last 4km at HM goal pace",                         False),
    (22, "Race-Specific", "Intervals",       7, 8, "2km wu + 5x1km at tempo w/ 90s jog + 1km cd",     19,  "Easy pace",                                              False),
    (23, "Race-Specific", "Race simulation", 8, 10, "2km wu + 6km at HM goal pace + 2km cd",          20,  "Easy, last 5km at HM goal pace - practice fueling",      False),
    (24, "Race-Specific", "CUTBACK week",    6, 6, "Easy conversational pace",                        14,  "Easy pace - recovery week",                              True),
    (25, "Peak/Taper", "Big long run",   7, 8, "2km wu + 4km at HM goal pace + 2km cd",               20,  "Easy, last 5km at HM goal pace",                         False),
    (26, "Peak/Taper", "PEAK WEEK",      7, 7, "2km wu + 4x1km at tempo w/ 90s jog + 1km cd",         21,  "Peak long run - easy pace, practice race fueling",       False),
    (27, "Peak/Taper", "Taper starts",   6, 6, "1km wu + 3km at HM goal pace + 2km cd",               16,  "Easy pace - volume dropping",                            False),
    (28, "Peak/Taper", "Taper",          5, 5, "1km wu + 2km at HM goal pace + 2km cd",               12,  "Easy pace",                                              False),
    (29, "Peak/Taper", "Race week -1",   5, 4, "3km easy + 4x100m strides",                           8,   "Easy pace, legs should feel fresh",                      False),
    (30, "Peak/Taper", "RACE WEEK",      4, 3, "Very easy + 2x100m strides",                          21.1,"RACE DAY! Half Marathon",                                False),
]


def classify_quality(detail):
    """Return (run_type, planned_pace, pace_range) for a quality workout description."""
    d = detail.lower()
    if "hm goal pace" in d or "hm pace" in d:
        return "HM Pace", PACE_HM, PACE_RANGE_HM
    if "strides" in d:
        return "Strides", PACE_EASY, PACE_RANGE_EASY
    if "tempo" in d or "1km at tempo" in d:
        return "Tempo", PACE_TEMPO, PACE_RANGE_TEMPO
    return "Steady", PACE_EASY, PACE_RANGE_EASY


def week_dates(week_num):
    """Return (Tue, Thu, Sun) dates for a given week."""
    monday = START_DATE + timedelta(weeks=week_num - 1)
    return (
        monday + timedelta(days=1),
        monday + timedelta(days=3),
        monday + timedelta(days=6),
    )


def build_plan():
    runs = []
    run_id = 1
    for wk, phase, focus, easy_km, q_km, q_detail, long_km, long_detail, cutback in PLAN:
        tue, thu, sun = week_dates(wk)
        monday = tue - timedelta(days=1)

        # Tuesday - Easy
        runs.append({
            "run_id":         f"R{run_id:03d}",
            "week":           wk,
            "week_start":     monday.isoformat(),
            "phase":          phase,
            "focus":          focus,
            "cutback":        cutback,
            "date":           tue.isoformat(),
            "day":            "Tuesday",
            "run_type":       "Easy",
            "planned_km":     easy_km,
            "planned_pace":   PACE_EASY,
            "pace_range":     PACE_RANGE_EASY,
            "workout_detail": "Easy conversational pace",
        })
        run_id += 1

        # Thursday - Quality
        q_type, q_pace, q_range = classify_quality(q_detail)
        runs.append({
            "run_id":         f"R{run_id:03d}",
            "week":           wk,
            "week_start":     monday.isoformat(),
            "phase":          phase,
            "focus":          focus,
            "cutback":        cutback,
            "date":           thu.isoformat(),
            "day":            "Thursday",
            "run_type":       q_type,
            "planned_km":     q_km,
            "planned_pace":   q_pace,
            "pace_range":     q_range,
            "workout_detail": q_detail,
        })
        run_id += 1

        # Sunday - Long (or Race in week 30)
        is_race = (wk == 30)
        long_type = "Race" if is_race else "Long"
        long_pace = PACE_RACE if is_race else PACE_LONG
        long_range = PACE_RANGE_HM if is_race else PACE_RANGE_LONG
        runs.append({
            "run_id":         f"R{run_id:03d}",
            "week":           wk,
            "week_start":     monday.isoformat(),
            "phase":          phase,
            "focus":          focus,
            "cutback":        cutback,
            "date":           sun.isoformat(),
            "day":            "Sunday",
            "run_type":       long_type,
            "planned_km":     long_km,
            "planned_pace":   long_pace,
            "pace_range":     long_range,
            "workout_detail": long_detail,
            "is_race":        is_race,
        })
        run_id += 1

    plan_json = {
        "meta": {
            "race_name":              RACE_NAME,
            "race_date":              RACE_DATE.isoformat(),
            "start_date":             START_DATE.isoformat(),
            "goal_time":              GOAL_TIME,
            "baseline_5k_pace_min":   BASELINE_5K_PACE_MIN,
            "total_weeks":            30,
            "runs_per_week":          3,
            "phases": [
                {"name": "Base",           "weeks": [1, 2, 3, 4, 5, 6, 7, 8]},
                {"name": "Endurance",      "weeks": [9, 10, 11, 12, 13, 14, 15, 16]},
                {"name": "Race-Specific",  "weeks": [17, 18, 19, 20, 21, 22, 23, 24]},
                {"name": "Peak/Taper",     "weeks": [25, 26, 27, 28, 29, 30]},
            ],
        },
        "runs": runs,
    }
    return plan_json


if __name__ == "__main__":
    plan = build_plan()
    with open("data/training_plan.json", "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Wrote {len(plan['runs'])} runs across {plan['meta']['total_weeks']} weeks")
