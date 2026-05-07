# FitTrack — Daily Home Exercise Routine System

**DSA-221: Information Management | DSA-224: Information Presentation and Visualization**
Isabela State University — College of Computing Studies, ICT

---

## Stack

| Layer       | Technology               | Version       |
|-------------|--------------------------|---------------|
| Language    | Python                   | 3.14.4        |
| GUI         | CustomTkinter            | 5.2.2         |
| Database    | MySQL                    | 9.7.0 LTS     |
| Charts      | Matplotlib               | 3.10.9        |
| DB Driver   | mysql-connector-python   | 9.3.0         |

---

## Project Structure

```
fittrack/
├── main.py                  # Entry point — run this
├── .env.example             # Copy to .env and fill in credentials
├── requirements.txt         # Python dependencies
│
├── config/
│   └── db.py                # DB connection manager (singleton)
│
├── models/
│   ├── exercise.py          # Exercise CRUD queries
│   ├── daily_log.py         # Log CRUD + completion toggle
│   ├── food_entry.py        # Food intake CRUD
│   ├── streak.py            # Streak evaluation logic
│   └── user.py              # User read + calorie goal update
│
├── views/
│   ├── dashboard.py         # Main landing page
│   ├── exercises.py         # Exercise library management
│   ├── calories.py          # Calorie intake tracker
│   ├── weekly.py            # Weekly planner grid
│   └── progress.py          # Progress analytics page
│
├── components/
│   ├── sidebar.py           # Navigation sidebar
│   └── widgets.py           # Reusable UI components
│
├── utils/
│   ├── charts.py            # Matplotlib chart widgets
│   └── reminder.py          # Reminder messages + scheduler
│
└── database/
    └── schema.sql           # Full MySQL schema + seed data
```

---

## Setup Instructions

### Step 1 — Prerequisites

Make sure the following are installed:

- **Python 3.14.4** — https://python.org/downloads
- **MySQL 9.7.0 LTS** — https://dev.mysql.com/downloads/mysql

Verify installations:
```bash
python --version      # should print Python 3.14.4
mysql --version       # should print 9.7.x
```

---

### Step 2 — Clone / Download the project

Place the `fittrack/` folder anywhere on your machine.

---

### Step 3 — Create the virtual environment

```bash
cd fittrack
python -m venv venv
```

Activate it:

**Windows:**
```bash
.\.venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

---

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 5 — Set up the database

Log into MySQL and run the schema file:

```bash
mysql -u root -p < database/schema.sql
```

This will:
- Create the `fittrack_db` database
- Create all 5 tables with constraints
- Create all 5 views
- Insert a demo user and sample exercises, logs, food entries, and streak

Verify it worked:
```bash
mysql -u root -p fittrack_db
```
```sql
SHOW TABLES;
SELECT * FROM user;
SELECT * FROM v_today_routine WHERE user_id = 1;
```

---

### Step 6 — Configure environment

Copy the example env file:

```bash
cp .env.example .env
```

Open `.env` and fill in your MySQL credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fittrack_db
DB_USER=root
DB_PASSWORD=your_actual_password_here
APP_USER_ID=1
```

> **Never commit `.env` to version control.** It is listed in `.gitignore` by convention.

---

### Step 7 — Run the application

```bash
python main.py
```

The FitTrack window will open centred on your screen.

---

## Features

| Feature                      | Page        | DSA-221 | DSA-224 |
|------------------------------|-------------|---------|---------|
| Add / Edit / Delete exercise | Exercises   | ✅ CRUD  |         |
| Mark exercise complete       | Dashboard   | ✅ CRUD  |         |
| Log food intake              | Calories    | ✅ CRUD  |         |
| Delete food entry            | Calories    | ✅ CRUD  |         |
| Daily routine auto-filter    | Dashboard   | ✅ Read  |         |
| Calorie balance (net)        | Calories    |         | ✅ Donut chart |
| Weekly calorie trend         | Dashboard   |         | ✅ Bar chart   |
| Weekly exercise volume       | Weekly      |         | ✅ Bar chart   |
| Completion rate trend        | Progress    |         | ✅ Line chart  |
| 30-day activity heatmap      | Progress    |         | ✅ Heatmap     |
| 7-day streak strip           | Dashboard   |         | ✅ Tile grid   |
| Streak counter               | Dashboard   | ✅ Read  | ✅ KPI card    |
| Daily reminder banner        | Dashboard   |         |         |
| Toast notifications          | All pages   |         |         |
| Weekly planner grid          | Weekly      | ✅ Read  |         |

---

## Business Rules Enforced

| Rule | Where Enforced |
|------|---------------|
| Exercise name unique per user (BR-01) | DB unique constraint + app error message |
| Amount must be > 0 (BR-03) | App validation + DB CHECK constraint |
| Calories must be > 0 (BR-05) | App validation + DB CHECK constraint |
| No duplicate log per day (BR-09) | DB unique constraint (INSERT IGNORE) |
| Net calories never stored (BR-13) | Computed on demand, no DB column |
| Streak only counts completed days (BR-15) | `streak.py` refresh logic |

---

## Troubleshooting

**App opens but shows no exercises:**
- Make sure you ran `schema.sql` which includes seed data.
- Check `APP_USER_ID=1` in your `.env`.

**MySQL connection refused:**
- Ensure MySQL service is running: `sudo systemctl start mysql` (Linux) or start MySQL from System Preferences (macOS).
- Double-check the password in `.env`.

**`ModuleNotFoundError: No module named 'customtkinter'`:**
- Make sure your virtual environment is activated before running.
- Re-run `pip install -r requirements.txt`.

**Charts appear blank:**
- This is a Matplotlib/TkAgg timing issue on first load.
- Navigate away and back to the page — the chart will render on `on_show()`.

---

## Database Schema Overview

```
user (1) ──────────────── (N) exercise
  │                              │
  │                              │ (N)
  │                              ▼
  ├────────────────────── (N) daily_log
  │
  ├────────────────────── (N) food_entry
  │
  └────────────────────── (1) streak
```

All foreign keys use `ON DELETE CASCADE`.
Schema is normalised to **Third Normal Form (3NF)**.

---

## Academic Compliance

### DSA-221 — Information Management
- CRUD operations: ✅ All four operations on `exercise` and `food_entry`
- Relational database: ✅ MySQL 9.7.0 LTS, 5 tables
- Normalisation: ✅ UNF → 1NF → 2NF → 3NF (documented in project report)
- Business rules: ✅ 17 rules, enforced at app and DB layers
- ERD: ✅ Documented in project report

### DSA-224 — Information Presentation and Visualization
- Dashboard: ✅ Unified view with 5 chart types
- Visualisation types: ✅ Donut, Bar (×2), Line, Heatmap, Tile grid
- Justification: ✅ Each chart type chosen for its data type (documented in report)
- Target users: ✅ Home fitness enthusiasts, defined in report
- Key decisions: ✅ Calorie balance, load balancing, consistency tracking
