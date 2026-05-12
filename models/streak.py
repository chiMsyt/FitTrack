# models/streak.py
from datetime import date, timedelta
from config.db import db, DBError


def get_streak(user_id):
    sql = """
        SELECT streak_id, current_streak, best_streak, last_active_date
        FROM streak WHERE user_id = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchone()


def refresh_streak(user_id):
    """
    Streak increments only when ALL exercises scheduled for today are completed.
    Unticking an exercise that drops completion below total does not revert an
    already-awarded streak — but the day is only counted once.
    """
    today     = date.today()
    yesterday = today - timedelta(days=1)

    # Check if today is fully complete (done == total scheduled)
    completion_sql = """
        SELECT COUNT(*) AS total, SUM(is_completed) AS done
        FROM daily_log WHERE user_id = %s AND log_date = CURRENT_DATE
    """
    with db.cursor() as cur:
        cur.execute(completion_sql, (user_id,))
        row = cur.fetchone()

    total = int(row['total']) if row and row['total'] else 0
    done  = int(row['done'])  if row and row['done']  else 0
    fully_complete = (total > 0 and done == total)

    streak = get_streak(user_id)
    if streak is None:
        _create_streak(user_id)
        streak = {'current_streak': 0, 'best_streak': 0, 'last_active_date': None}

    current   = streak['current_streak']
    best      = streak['best_streak']
    last_date = streak['last_active_date']

    if fully_complete:
        if last_date == today:
            pass  # already counted today
        elif last_date == yesterday:
            current += 1
        else:
            current = 1
        last_date = today

    best = max(best, current)

    update_sql = """
        UPDATE streak
        SET current_streak=%s, best_streak=%s, last_active_date=%s
        WHERE user_id=%s
    """
    with db.cursor() as cur:
        cur.execute(update_sql, (current, best, last_date, user_id))

    return {'current_streak': current, 'best_streak': best, 'last_active_date': last_date}


def _create_streak(user_id):
    sql = "INSERT IGNORE INTO streak (user_id, current_streak, best_streak) VALUES (%s, 0, 0)"
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
