# models/weight_log.py
from config.db import db, DBError


def log_weight(user_id, exercise_id, weight_kg, reps, sets=1, notes=None):
    sql = """
        INSERT INTO weight_log (user_id, exercise_id, log_date, weight_kg, reps, `sets`, notes)
        VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s)
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, exercise_id, weight_kg, reps, sets, notes or None))
        return cur.lastrowid


def get_weight_history(user_id, exercise_id):
    """All weight entries for one exercise, ordered by date. Used for progression chart."""
    sql = """
        SELECT wlog_id, log_date, weight_kg, reps, `sets`, notes
        FROM weight_log
        WHERE user_id = %s AND exercise_id = %s
        ORDER BY log_date ASC, wlog_id ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, exercise_id))
        return cur.fetchall()


def get_progress_view(user_id, exercise_id=None):
    """Best weight per day per exercise. Optionally filtered to one exercise."""
    if exercise_id:
        sql = """
            SELECT exercise_id, exercise_name, log_date, max_weight_kg, total_reps, max_reps
            FROM v_weight_progress
            WHERE user_id = %s AND exercise_id = %s
            ORDER BY log_date ASC
        """
        with db.cursor() as cur:
            cur.execute(sql, (user_id, exercise_id))
            return cur.fetchall()
    else:
        sql = """
            SELECT exercise_id, exercise_name, log_date, max_weight_kg, total_reps, max_reps
            FROM v_weight_progress WHERE user_id = %s ORDER BY exercise_id, log_date ASC
        """
        with db.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()


def get_weighted_exercises(user_id):
    """Return exercises of type Weighted for the weight log selector."""
    sql = """
        SELECT exercise_id, name, target_muscle
        FROM exercise
        WHERE user_id = %s AND exercise_type = 'Weighted'
        ORDER BY name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def delete_weight_entry(wlog_id, user_id):
    sql = "DELETE FROM weight_log WHERE wlog_id = %s AND user_id = %s"
    with db.cursor() as cur:
        cur.execute(sql, (wlog_id, user_id))
        return cur.rowcount > 0
