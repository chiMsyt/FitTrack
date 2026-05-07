# models/food_entry.py
# =============================================================================
# Food entry model — all SQL for the `food_entry` table.
#
# Handles the calorie intake side of the net-calorie calculation.
# The net balance itself is a derived value (consumed - burned) and is
# never persisted — it is computed on demand by the view or the calories
# view layer. This satisfies BR-13 and keeps the schema in 3NF.
# =============================================================================

from config.db import db, DBError


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def create_food_entry(
    user_id: int,
    food_name: str,
    calories_kcal: int,
    meal_type: str,          # "Breakfast" | "Lunch" | "Dinner" | "Snack"
) -> int:
    """
    Log a new food entry for today.
    Returns the new entry_id.
    entry_date defaults to CURRENT_DATE in the schema (no arg needed).
    """
    sql = """
        INSERT INTO food_entry (user_id, food_name, calories_kcal, meal_type)
        VALUES (%s, %s, %s, %s)
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, food_name, calories_kcal, meal_type))
        return cur.lastrowid


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def get_todays_food(user_id: int) -> list[dict]:
    """
    Return all food entries logged today, ordered by meal type then entry_id.
    Columns: entry_id, food_name, calories_kcal, meal_type, entry_date.
    """
    sql = """
        SELECT entry_id, food_name, calories_kcal, meal_type, entry_date
        FROM   food_entry
        WHERE  user_id    = %s
          AND  entry_date = CURRENT_DATE
        ORDER  BY
            FIELD(meal_type, 'Breakfast', 'Lunch', 'Dinner', 'Snack'),
            entry_id ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_total_consumed_today(user_id: int) -> int:
    """
    Return total kcal consumed today.
    Returns 0 if no entries exist.
    """
    sql = """
        SELECT COALESCE(SUM(calories_kcal), 0) AS total
        FROM   food_entry
        WHERE  user_id    = %s
          AND  entry_date = CURRENT_DATE
    """
    with db.cursor(dictionary=False) as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_daily_summary(user_id: int) -> dict | None:
    """
    Return the full daily calorie summary for today using
    v_daily_calorie_summary view.
    Columns: entry_date, total_consumed, total_burned, net_calories.
    Returns None if no food has been logged today.
    """
    sql = """
        SELECT entry_date, total_consumed, total_burned, net_calories
        FROM   v_daily_calorie_summary
        WHERE  user_id    = %s
          AND  entry_date = CURRENT_DATE
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchone()


def get_weekly_calorie_trend(user_id: int) -> list[dict]:
    """
    Return net calorie data for the past 7 days.
    Used by the dashboard weekly calorie bar chart.
    Columns: entry_date, total_consumed, total_burned, net_calories.
    """
    sql = """
        SELECT entry_date, total_consumed, total_burned, net_calories
        FROM   v_daily_calorie_summary
        WHERE  user_id    = %s
          AND  entry_date >= DATE_SUB(CURRENT_DATE, INTERVAL 6 DAY)
        ORDER  BY entry_date ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def update_food_entry(
    entry_id: int,
    user_id: int,
    food_name: str,
    calories_kcal: int,
    meal_type: str,
) -> bool:
    """
    Update a food entry's name, calories, and meal type.
    Returns True if a row was updated.
    """
    sql = """
        UPDATE food_entry
        SET    food_name     = %s,
               calories_kcal = %s,
               meal_type     = %s
        WHERE  entry_id = %s AND user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (food_name, calories_kcal, meal_type, entry_id, user_id))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_food_entry(entry_id: int, user_id: int) -> bool:
    """
    Remove a food entry by ID.
    user_id guard prevents cross-user deletion.
    Returns True if a row was deleted.
    """
    sql = """
        DELETE FROM food_entry
        WHERE  entry_id = %s AND user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (entry_id, user_id))
        return cur.rowcount > 0
