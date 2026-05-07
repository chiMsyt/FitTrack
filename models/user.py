# models/user.py
# =============================================================================
# User model — reads and updates the `user` table.
# Kept minimal: FitTrack is single-user in this implementation
# (the active user_id is loaded from .env at startup).
# Extensible to multi-user by adding a login view later.
# =============================================================================

from config.db import db, DBError


def get_user(user_id: int) -> dict | None:
    """
    Return user record by ID.
    Columns: user_id, username, email, calorie_goal, created_at.
    """
    sql = """
        SELECT user_id, username, email, calorie_goal, created_at
        FROM   user
        WHERE  user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchone()


def update_calorie_goal(user_id: int, new_goal: int) -> bool:
    """
    Update the user's daily calorie target.
    Returns True if updated. Raises DBError if goal <= 0 (CHECK constraint).
    """
    sql = """
        UPDATE user
        SET    calorie_goal = %s
        WHERE  user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (new_goal, user_id))
        return cur.rowcount > 0
