# tools/generate_data.py
# =============================================================================
# FitTrack — Realistic Dataset Generator
#
# Usage:
#   python tools/generate_data.py
#
# Interactive prompts let you configure:
#   - How many days back to generate (up to 365)
#   - Calorie mode: deficit or surplus
#   - Starting and target weights for weighted exercises (simulates progression)
#   - Rest day pattern (e.g. rest on Sundays)
#
# Run AFTER schema.sql has been applied. Clears existing data for user_id=1
# before inserting so you can re-run freely.
# =============================================================================

import os, sys, random
from datetime import date, timedelta
from decimal import Decimal

# Add project root to path so config/models are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.db import db


# ── Realistic food banks by mode ────────────────────────────────────────────

DEFICIT_FOODS = [
    ("Oatmeal with berries",         320, "Breakfast"),
    ("Scrambled eggs (2)",           220, "Breakfast"),
    ("Greek yogurt with honey",      180, "Breakfast"),
    ("Grilled chicken breast",       280, "Lunch"),
    ("Brown rice and veggies",       310, "Lunch"),
    ("Tuna salad wrap",              350, "Lunch"),
    ("Protein shake",                160, "Snack"),
    ("Apple with peanut butter",     210, "Snack"),
    ("Rice cake",                     80, "Snack"),
    ("Grilled salmon and salad",     380, "Dinner"),
    ("Chicken stir fry",             420, "Dinner"),
    ("Veggie soup",                  190, "Dinner"),
]

SURPLUS_FOODS = [
    ("Oatmeal with banana and nuts", 520, "Breakfast"),
    ("4 scrambled eggs with toast",  480, "Breakfast"),
    ("Mass gainer shake",            700, "Breakfast"),
    ("Chicken rice and avocado",     650, "Lunch"),
    ("Pasta with ground beef",       720, "Lunch"),
    ("Peanut butter sandwich x2",    560, "Lunch"),
    ("Protein bar",                  280, "Snack"),
    ("Mixed nuts and raisins",       320, "Snack"),
    ("Banana and peanut butter",     290, "Snack"),
    ("Steak and sweet potato",       780, "Dinner"),
    ("Salmon rice bowl",             680, "Dinner"),
    ("Beef and veggie pasta",        750, "Dinner"),
]

# ── Exercise progression helpers ─────────────────────────────────────────────

def lerp(start, end, t):
    """Linear interpolation between start and end."""
    return start + (end - start) * t


def generate_weight_progression(start_kg, end_kg, days_list):
    """
    Given a sorted list of dates, return a weight for each date
    that increases linearly from start_kg to end_kg with small noise.
    """
    if not days_list:
        return []
    n = len(days_list)
    result = []
    for i, d in enumerate(days_list):
        t = i / max(n - 1, 1)
        base = lerp(start_kg, end_kg, t)
        # Add small realistic noise: ±2.5 kg
        noise = random.uniform(-2.5, 2.5)
        weight = round(max(start_kg * 0.9, base + noise) * 2) / 2  # round to 0.5 kg
        result.append((d, weight))
    return result


# ── Main generator ───────────────────────────────────────────────────────────

def prompt(msg, default=None, cast=str):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{msg}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    try:
        return cast(raw)
    except (ValueError, TypeError):
        print(f"  Invalid input, using default: {default}")
        return default


def main():
    print("\n=== FitTrack Data Generator ===\n")

    days_back   = prompt("How many days of data to generate? (1-365)", 365, int)
    days_back   = max(1, min(365, days_back))
    mode        = prompt("Calorie mode? [deficit / surplus]", "deficit").lower()
    if mode not in ("deficit", "surplus"):
        mode = "deficit"

    rest_day    = prompt("Which day is rest? (Mon/Tue/Wed/Thu/Fri/Sat/Sun/None)", "Sun")
    streak_prob = prompt("Probability of completing all exercises on active days? (0.0-1.0)", 0.80, float)
    streak_prob = max(0.0, min(1.0, streak_prob))

    # Weighted exercise progression params
    print("\nWeighted exercise progression (press Enter to skip a lift):")
    bench_start = prompt("  Bench Press starting weight kg", 20.0, float)
    bench_end   = prompt("  Bench Press target weight kg",  50.0, float)
    squat_start = prompt("  Squat starting weight kg",      40.0, float)
    squat_end   = prompt("  Squat target weight kg",        80.0, float)
    leg_start   = prompt("  Leg Press starting weight kg",  50.0, float)
    leg_end     = prompt("  Leg Press target weight kg",   150.0, float)
    cable_start = prompt("  Cable Row starting weight kg",  20.0, float)
    cable_end   = prompt("  Cable Row target weight kg",    45.0, float)

    print(f"\nGenerating {days_back} days of {mode} data...")

    db.connect()

    with db.cursor() as cur:
        # Clear existing generated data for user_id=1
        cur.execute("DELETE FROM weight_log WHERE user_id = 1")
        cur.execute("DELETE FROM food_entry WHERE user_id = 1")
        cur.execute("DELETE FROM daily_log WHERE user_id = 1")
        cur.execute("UPDATE streak SET current_streak=0, best_streak=0, last_active_date=NULL WHERE user_id=1")

        # Update calorie mode
        goal = 1800 if mode == "deficit" else 3200
        surplus_goal = 3500 if mode == "surplus" else None
        cur.execute(
            "UPDATE user SET calorie_goal=%s, calorie_mode=%s, surplus_goal=%s WHERE user_id=1",
            (goal, mode, surplus_goal)
        )

    food_bank = DEFICIT_FOODS if mode == "deficit" else SURPLUS_FOODS

    today = date.today()
    start = today - timedelta(days=days_back - 1)

    # Fetch exercise list
    with db.cursor() as cur:
        cur.execute("SELECT exercise_id, name, scheduled_day, exercise_type FROM exercise WHERE user_id=1")
        exercises = cur.fetchall()

    day_map = {
        "Mon":0,"Tue":1,"Wed":2,"Thu":3,"Fri":4,"Sat":5,"Sun":6
    }
    rest_idx = day_map.get(rest_day, -1)

    # Weighted exercise day lists (for progression)
    bench_days, squat_days, leg_days, cable_days = [], [], [], []

    # Pass 1 — identify weighted exercise dates
    d = start
    while d <= today:
        if d.weekday() == rest_idx:
            d += timedelta(days=1)
            continue
        dow = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d.weekday()]
        for ex in exercises:
            if ex["scheduled_day"] == "Daily" or ex["scheduled_day"] == dow:
                if ex["exercise_type"] == "Weighted":
                    name = ex["name"]
                    if "Bench" in name:   bench_days.append(d)
                    elif "Squat" in name: squat_days.append(d)
                    elif "Leg Press" in name: leg_days.append(d)
                    elif "Cable" in name: cable_days.append(d)
        d += timedelta(days=1)

    bench_prog  = dict(generate_weight_progression(bench_start,  bench_end,  sorted(set(bench_days))))
    squat_prog  = dict(generate_weight_progression(squat_start,  squat_end,  sorted(set(squat_days))))
    leg_prog    = dict(generate_weight_progression(leg_start,    leg_end,    sorted(set(leg_days))))
    cable_prog  = dict(generate_weight_progression(cable_start,  cable_end,  sorted(set(cable_days))))

    log_rows    = []
    food_rows   = []
    weight_rows = []

    current_streak = 0
    best_streak    = 0
    last_active    = None

    d = start
    while d <= today:
        is_rest = (d.weekday() == rest_idx)
        dow     = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d.weekday()]

        if not is_rest:
            # Determine today's exercises
            todays_exs = [e for e in exercises
                          if e["scheduled_day"] == "Daily" or e["scheduled_day"] == dow]

            # Vary completion probability slightly by week for realistic wave pattern
            week_num = (d - start).days // 7
            week_factor = 0.1 * (week_num % 3 - 1)  # slight wave: -0.1, 0, +0.1
            effective_prob = max(0.5, min(0.95, streak_prob + week_factor))
            fully_done = random.random() < effective_prob

            for ex in todays_exs:
                if d == today:
                    # Skip today entirely — app will seed today's logs on launch
                    continue
                is_done = 1 if fully_done else (1 if random.random() < 0.5 else 0)
                comp_at = f"{d} {random.randint(7,20):02d}:{random.randint(0,59):02d}:00" if is_done else None
                log_rows.append((1, ex["exercise_id"], str(d), is_done, comp_at))

                # Weight log
                if ex["exercise_type"] == "Weighted" and is_done:
                    name = ex["name"]
                    if "Bench"     in name: w = bench_prog.get(d)
                    elif "Squat"   in name: w = squat_prog.get(d)
                    elif "Leg"     in name: w = leg_prog.get(d)
                    elif "Cable"   in name: w = cable_prog.get(d)
                    else:                   w = None
                    if w:
                        reps = random.randint(6, 12)
                        sets = random.randint(3, 4)
                        weight_rows.append((1, ex["exercise_id"], str(d), float(w), reps, sets))

            # Streak tracking
            if fully_done and d != today:
                if last_active == d - timedelta(days=1):
                    current_streak += 1
                else:
                    current_streak = 1
                last_active = d
                best_streak = max(best_streak, current_streak)

        # Food entries (1–4 entries per active day)
        if not is_rest or random.random() < 0.4:
            meals_today = random.sample(food_bank, k=random.randint(2, 4))
            for food_name, kcal, meal_type in meals_today:
                # add minor calorie variation
                kcal_var = kcal + random.randint(-30, 30)
                food_rows.append((1, food_name, max(0, kcal_var), meal_type, str(d)))

        d += timedelta(days=1)

    # Bulk insert
    with db.cursor() as cur:
        if log_rows:
            cur.executemany(
                "INSERT IGNORE INTO daily_log (user_id,exercise_id,log_date,is_completed,completed_at) VALUES (%s,%s,%s,%s,%s)",
                log_rows
            )
        if food_rows:
            cur.executemany(
                "INSERT INTO food_entry (user_id,food_name,calories_kcal,meal_type,entry_date) VALUES (%s,%s,%s,%s,%s)",
                food_rows
            )
        if weight_rows:
            cur.executemany(
                "INSERT INTO weight_log (user_id,exercise_id,log_date,weight_kg,reps,`sets`) VALUES (%s,%s,%s,%s,%s,%s)",
                weight_rows
            )
        cur.execute(
            "UPDATE streak SET current_streak=%s, best_streak=%s, last_active_date=%s WHERE user_id=1",
            (current_streak, best_streak, str(last_active) if last_active else None)
        )

    db.disconnect()

    print(f"\nDone!")
    print(f"  Log entries:    {len(log_rows)}")
    print(f"  Food entries:   {len(food_rows)}")
    print(f"  Weight entries: {len(weight_rows)}")
    print(f"  Streak:         {current_streak} days (best: {best_streak})")


if __name__ == "__main__":
    main()
