# models/exercise.py
from config.db import db, DBError


def create_exercise(user_id, name, exercise_type, amount, category,
                    est_calories, target_muscle, scheduled_day, notes=None):
    sql = """
        INSERT INTO exercise
            (user_id, name, exercise_type, amount, category,
             est_calories, target_muscle, scheduled_day, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, name, exercise_type, amount, category,
                          est_calories, target_muscle or None,
                          scheduled_day, notes or None))
        return cur.lastrowid


def get_all_exercises(user_id):
    sql = """
        SELECT exercise_id, name, exercise_type, amount, category,
               est_calories, target_muscle, scheduled_day, notes
        FROM exercise WHERE user_id = %s ORDER BY name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_exercise_by_id(exercise_id, user_id):
    sql = """
        SELECT exercise_id, name, exercise_type, amount, category,
               est_calories, target_muscle, scheduled_day, notes
        FROM exercise WHERE exercise_id = %s AND user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (exercise_id, user_id))
        return cur.fetchone()


def get_today_exercises(user_id):
    sql = """
        SELECT exercise_id, exercise_name AS name, exercise_type, amount,
               category, est_calories, target_muscle, scheduled_day,
               notes, is_completed, completed_at
        FROM v_today_routine WHERE user_id = %s ORDER BY exercise_name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_exercises_by_day(user_id, day):
    sql = """
        SELECT exercise_id, name, exercise_type, amount, category,
               est_calories, target_muscle, scheduled_day, notes
        FROM exercise
        WHERE user_id = %s AND (scheduled_day = %s OR scheduled_day = 'Daily')
        ORDER BY name ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, day))
        return cur.fetchall()


def update_exercise(exercise_id, user_id, name, exercise_type, amount,
                    category, est_calories, target_muscle, scheduled_day, notes=None):
    sql = """
        UPDATE exercise
        SET name=%s, exercise_type=%s, amount=%s, category=%s,
            est_calories=%s, target_muscle=%s, scheduled_day=%s, notes=%s
        WHERE exercise_id=%s AND user_id=%s
    """
    with db.cursor() as cur:
        cur.execute(sql, (name, exercise_type, amount, category,
                          est_calories, target_muscle or None,
                          scheduled_day, notes or None,
                          exercise_id, user_id))
        return cur.rowcount > 0


def delete_exercise(exercise_id, user_id):
    sql = "DELETE FROM exercise WHERE exercise_id = %s AND user_id = %s"
    with db.cursor() as cur:
        cur.execute(sql, (exercise_id, user_id))
        return cur.rowcount > 0


def get_total_calories_burned_today(user_id):
    sql = """
        SELECT COALESCE(SUM(e.est_calories), 0)
        FROM daily_log dl
        JOIN exercise e ON e.exercise_id = dl.exercise_id
        WHERE dl.user_id = %s AND dl.log_date = CURRENT_DATE AND dl.is_completed = 1
    """
    with db.cursor(dictionary=False) as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_weekly_volume(user_id):
    sql = """
        SELECT scheduled_day, category, exercise_count
        FROM v_exercise_volume_weekly WHERE user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()
