# models/streak.py
# =============================================================================
# Streak model — reads and updates the `streak` table.
#
# Streak logic explained:
#   The streak table holds one row per user (1:1). It is updated by
#   refresh_streak() which is called once per app session on startup.
#
#   Rules (from business rules BR-15, BR-16):
#     - If last_active_date == yesterday → increment current_streak
#     - If last_active_date == today     → already counted, no change
#     - Anything else                    → streak broken, reset to 0
#     - best_streak is updated whenever current_streak exceeds it
#
#   Whether "today" counts as active is determined by checking if at least
#   one exercise was completed today in daily_log. This avoids storing a
#   derived boolean in the streak table (3NF compliance).
# =============================================================================

from datetime import date, timedelta

from config.db import db, DBError


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def get_streak(user_id: int) -> dict | None:
    """
    Return the streak record for a user.
    Columns: streak_id, current_streak, best_streak, last_active_date.
    Returns None if no streak record exists yet (shouldn't happen after seed).
    """
    sql = """
        SELECT streak_id, current_streak, best_streak, last_active_date
        FROM   streak
        WHERE  user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchone()


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def refresh_streak(user_id: int) -> dict:
    """
    Evaluate and update the user's streak based on today's activity.

    Steps:
      1. Check if any exercise was completed today in daily_log.
      2. Compare last_active_date to today/yesterday.
      3. Increment, maintain, or reset current_streak accordingly.
      4. Update best_streak if current_streak surpasses it.
      5. Return the updated streak dict.

    This is the only function that writes to the streak table —
    all streak mutations are centralised here.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Step 1: check today's activity
    activity_sql = """
        SELECT COUNT(*) AS done_today
        FROM   daily_log
        WHERE  user_id      = %s
          AND  log_date     = CURRENT_DATE
          AND  is_completed  = 1
    """
    with db.cursor(dictionary=False) as cur:
        cur.execute(activity_sql, (user_id,))
        row = cur.fetchone()
        done_today = int(row[0]) if row else 0

    # Step 2: fetch current streak record
    streak = get_streak(user_id)
    if streak is None:
        # Create a default record if missing (edge case: new user, no seed)
        _create_streak(user_id)
        streak = {"current_streak": 0, "best_streak": 0, "last_active_date": None}

    current   = streak["current_streak"]
    best      = streak["best_streak"]
    last_date = streak["last_active_date"]   # date object or None

    # Step 3: evaluate
    if done_today > 0:
        if last_date == today:
            # Already counted today — no change needed
            pass
        elif last_date == yesterday:
            # Consecutive day — extend the streak
            current += 1
        else:
            # Gap in activity (or first ever completion) — reset to 1
            current = 1

        last_date = today
    # else: nothing done today — streak stays as-is (not broken until tomorrow)

    # Step 4: update best
    best = max(best, current)

    # Step 5: persist
    update_sql = """
        UPDATE streak
        SET    current_streak   = %s,
               best_streak      = %s,
               last_active_date = %s
        WHERE  user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(update_sql, (current, best, last_date, user_id))

    return {
        "current_streak":   current,
        "best_streak":      best,
        "last_active_date": last_date,
    }


def _create_streak(user_id: int) -> None:
    """
    Insert a default streak record for a user.
    Private — only called by refresh_streak as a safety fallback.
    """
    sql = """
        INSERT IGNORE INTO streak (user_id, current_streak, best_streak)
        VALUES (%s, 0, 0)
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
