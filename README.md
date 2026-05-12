# FitTrack — Daily Home Exercise Routine System

**DSA-221: Information Management | DSA-224: Information Presentation and Visualization**
Isabela State University — College of Computing Studies, ICT

---

## Stack

| Layer    | Technology             | Version   |
|----------|------------------------|-----------|
| Language | Python                 | 3.14.4    |
| GUI      | CustomTkinter          | 5.2.2     |
| Database | MySQL                  | 9.7.0 LTS |
| Charts   | Matplotlib             | 3.10.9    |
| Images   | Pillow                 | 12.0.0    |
| DB Driver| mysql-connector-python | 9.3.0     |

---

## Project Structure

```
fittrack/
├── main.py
├── .env.example
├── requirements.txt
├── config/
│   └── db.py
├── models/
│   ├── exercise.py
│   ├── daily_log.py
│   ├── food_entry.py
│   ├── streak.py
│   ├── user.py
│   └── weight_log.py          # NEW — weight progression tracking
├── views/
│   ├── dashboard.py           # Summary-only (metrics, streak, calorie chart)
│   ├── exercises.py           # Library + Log Weight tabs
│   ├── calories.py            # Deficit / Surplus toggle + donut charts
│   ├── weekly.py              # Today's Routine (interactive) + 7-day grid
│   └── progress.py            # Activity tab + Weight Progress tab
├── components/
│   ├── sidebar.py
│   └── widgets.py
├── utils/
│   ├── charts.py
│   └── reminder.py
├── tools/
│   └── generate_data.py       # NEW — realistic dataset generator
└── database/
    └── schema.sql
```

---

## Setup

### 1. Prerequisites
- Python 3.14.4
- MySQL 9.7.0 LTS

### 2. Virtual environment
```bash
cd fittrack
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Database
```bash
mysql -u root -p < database/schema.sql
```

### 5. Configure credentials
```bash
cp .env.example .env
# Edit .env with your MySQL password
```

### 6. Run
```bash
python main.py
```

---

## Generating Test Data

Run the interactive data generator to populate realistic data (up to 1 year):

```bash
python tools/generate_data.py
```

You will be prompted for:
- Number of days (1–365)
- Calorie mode (deficit / surplus)
- Rest day
- Completion probability
- Starting and target weights for each weighted exercise

**Warning:** This clears existing data for the demo user before inserting.

---

## Features

| Feature | Page | DSA-221 | DSA-224 |
|---------|------|---------|---------|
| Add / Edit / Delete exercise | Exercises | ✅ CRUD | |
| Category + notes per exercise | Exercises | ✅ | |
| Log weight sessions | Exercises → Log Weight tab | ✅ CRUD | |
| Mark exercises complete | Weekly Plan → Today's Routine | ✅ CRUD | |
| Streak — full completion only | Weekly Plan / Dashboard | ✅ | |
| Log food intake | Calories | ✅ CRUD | |
| Deficit mode (shrinking donut) | Calories | | ✅ Donut chart |
| Surplus mode (two donuts) | Calories | | ✅ Donut ×2 |
| Weekly calorie trend | Dashboard | | ✅ Bar chart |
| Workload by category (stacked) | Weekly Plan | | ✅ Stacked bar |
| Completion rate trend | Progress → Activity | | ✅ Line chart |
| 30-day activity heatmap | Progress → Activity | | ✅ Heatmap |
| 7-day streak strip | Dashboard | | ✅ Tile strip |
| Weight progression per lift | Progress → Weight Progress | | ✅ Line chart |
| KPI metric cards | Dashboard / Calories / Progress | | ✅ KPI cards |

---

## Database Schema — v2

### Tables (6)
| Table | Purpose |
|-------|---------|
| user | User account + calorie mode + surplus goal |
| exercise | Exercise library (category, notes; no difficulty) |
| daily_log | Per-exercise completion log |
| weight_log | Per-session weight/reps/sets for weighted exercises |
| food_entry | Daily food intake |
| streak | Current and best consecutive-day streak |

### Views (6)
| View | Used by |
|------|---------|
| v_today_routine | Weekly Plan — Today's Routine |
| v_daily_calorie_summary | Calories page |
| v_weekly_completion | Progress — completion line chart |
| v_exercise_volume_weekly | Weekly Plan — workload chart (by category) |
| v_30day_heatmap | Progress — heatmap |
| v_weight_progress | Progress — Weight Progress tab |

### Key schema changes from v1
- `difficulty` removed from `exercise` — replaced by user-defined `category` (Strength / Cardio / Core / Flexibility / Full Body)
- `notes` added to `exercise` (optional freetext)
- `exercise_type` gains `Weighted` option
- `user` gains `calorie_mode` (deficit/surplus) and `surplus_goal`
- New `weight_log` table and `v_weight_progress` view

---

## Normalization (3NF) — unchanged
Schema remains in Third Normal Form. `weight_log` is a proper fact table with FKs to `user` and `exercise`. Net calorie balance is never stored — always computed.

---

## Troubleshooting

**No exercises shown today:** Run schema.sql (includes seed data). Check `APP_USER_ID=1` in `.env`.

**MySQL connection refused:** Ensure MySQL is running. Verify password in `.env`.

**Charts appear blank:** Navigate away and back — charts render on `on_show()`.

**Weight Progress tab empty:** Log at least one weighted exercise session first in the Exercises → Log Weight tab.

**Surplus goal not saving:** Set mode to "surplus" first, then enter the surplus target and click Set.
