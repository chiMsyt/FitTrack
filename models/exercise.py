# models/exercise.py
# =============================================================================
# Exercise model — all SQL queries for the `exercise` table.
#
# Each function is a thin data-access method:
#   - Accepts plain Python types (str, int, etc.)
#   - Returns plain dicts or lists of dicts (no ORM objects)
#   - Never contains UI logic — that lives in views/
#
# All queries use parameterised statements (%s placeholders) to prevent
# SQL injection. Raw f-string SQL is never used with user-supplied data.
# =============================================================================

from config.db import db, DBError


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def create_exercise(
    user_id: int,
    name: str,
    exercise_type: str,   # "Reps" | "Duration"
    amount: int,
    difficulty: str,      # "Easy" | "Medium" | "Hard"
    est_calories: int,
    target_muscle: str | None,
    scheduled_day: str,   # "Mon".."Sun" | "Daily"
) -> int:
    """
    Insert a new exercise into the library.
    Returns the new exercise_id on success.
    Raises DBError if the name already exists for this user (BR-01).
    """
    sql = """
        INSERT INTO exercise
            (user_id, name, exercise_type, amount, difficulty,
             est_calories, target_muscle, scheduled_day)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with db.cursor() as cur:
        cur.execute(sql, (
            user_id, name, exercise_type, amount, difficulty,
            est_calories, target_muscle or None, scheduled_day
        ))
        return cur.lastrowid


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def get_all_exercises(user_id: int) -> list[dict]:
    """
    Return every exercise in the user's library, ordered alphabetically.
    Each row is a dict matching the exercise table columns.
    """
    sql = """
        SELECT exercise_id, name, exercise_type, amount, difficulty,
               est_calories, target_muscle, scheduled_day
        FROM   exercise
        WHERE  user_id = %s
        ORDER  BY name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_exercise_by_id(exercise_id: int, user_id: int) -> dict | None:
    """
    Return a single exercise record, or None if not found.
    user_id guard prevents cross-user data access.
    """
    sql = """
        SELECT exercise_id, name, exercise_type, amount, difficulty,
               est_calories, target_muscle, scheduled_day
        FROM   exercise
        WHERE  exercise_id = %s AND user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (exercise_id, user_id))
        return cur.fetchone()


def get_today_exercises(user_id: int) -> list[dict]:
    """
    Return today's exercises using the v_today_routine view.
    Includes is_completed and completed_at from the daily_log join.
    The view handles the day-of-week filtering logic entirely in SQL.
    """
    sql = """
        SELECT exercise_id, exercise_name AS name, exercise_type, amount, difficulty,
               est_calories, target_muscle, scheduled_day,
               is_completed, completed_at
        FROM   v_today_routine
        WHERE  user_id = %s
        ORDER  BY exercise_name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_exercises_by_day(user_id: int, day: str) -> list[dict]:
    """
    Return exercises scheduled for a specific day or marked Daily.
    Used by the weekly planner view.
    day: "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" | "Sun"
    """
    sql = """
        SELECT exercise_id, name, exercise_type, amount, difficulty,
               est_calories, target_muscle, scheduled_day
        FROM   exercise
        WHERE  user_id = %s
          AND  (scheduled_day = %s OR scheduled_day = 'Daily')
        ORDER  BY name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, day))
        return cur.fetchall()


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def update_exercise(
    exercise_id: int,
    user_id: int,
    name: str,
    exercise_type: str,
    amount: int,
    difficulty: str,
    est_calories: int,
    target_muscle: str | None,
    scheduled_day: str,
) -> bool:
    """
    Update all editable fields of an exercise.
    Returns True if a row was updated, False if exercise_id was not found.
    """
    sql = """
        UPDATE exercise
        SET    name          = %s,
               exercise_type = %s,
               amount        = %s,
               difficulty    = %s,
               est_calories  = %s,
               target_muscle = %s,
               scheduled_day = %s
        WHERE  exercise_id = %s AND user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (
            name, exercise_type, amount, difficulty,
            est_calories, target_muscle or None, scheduled_day,
            exercise_id, user_id
        ))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_exercise(exercise_id: int, user_id: int) -> bool:
    """
    Delete an exercise from the library.
    Cascades to daily_log entries via the FK constraint in schema.sql.
    Returns True if a row was deleted.
    """
    sql = """
        DELETE FROM exercise
        WHERE  exercise_id = %s AND user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (exercise_id, user_id))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# AGGREGATES (used by dashboard metrics)
# ---------------------------------------------------------------------------

def get_total_calories_burned_today(user_id: int) -> int:
    """
    Sum est_calories for all completed exercises today.
    Returns 0 if nothing has been completed yet.
    """
    sql = """
        SELECT COALESCE(SUM(e.est_calories), 0) AS total_burned
        FROM   daily_log dl
        JOIN   exercise  e  ON e.exercise_id = dl.exercise_id
        WHERE  dl.user_id     = %s
          AND  dl.log_date    = CURRENT_DATE
          AND  dl.is_completed = 1
    """
    with db.cursor(dictionary=False) as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_weekly_volume(user_id: int) -> list[dict]:
    """
    Return exercise count per scheduled day for the weekly planner chart.
    Uses the v_exercise_volume_weekly view.
    """
    sql = """
        SELECT scheduled_day, exercise_count
        FROM   v_exercise_volume_weekly
        WHERE  user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()
