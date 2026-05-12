# models/user.py
from config.db import db, DBError


def get_user(user_id):
    sql = """
        SELECT user_id, username, email, calorie_goal,
               calorie_mode, surplus_goal, created_at
        FROM user WHERE user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchone()


def update_calorie_goal(user_id, new_goal):
    sql = "UPDATE user SET calorie_goal = %s WHERE user_id = %s"
    with db.cursor() as cur:
        cur.execute(sql, (new_goal, user_id))
        return cur.rowcount > 0


def update_calorie_mode(user_id, mode, surplus_goal=None):
    """mode: 'deficit' or 'surplus'. surplus_goal only required for surplus mode."""
    sql = "UPDATE user SET calorie_mode = %s, surplus_goal = %s WHERE user_id = %s"
    with db.cursor() as cur:
        cur.execute(sql, (mode, surplus_goal, user_id))
        return cur.rowcount > 0
