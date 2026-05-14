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
    Streak logic:
    - Increments only when ALL exercises scheduled for today are completed.
    - Rest days (days with NO exercises scheduled) are skipped gracefully —
      they do not break the streak. The streak looks back to find the last
      non-rest day and checks if it was completed.
    - Unticking does not revert an already-awarded day.
    """
    today = date.today()

    # Check today's scheduled + completed count
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
    is_rest_day    = (total == 0)  # no exercises scheduled = rest day

    streak = get_streak(user_id)
    if streak is None:
        _create_streak(user_id)
        streak = {'current_streak': 0, 'best_streak': 0, 'last_active_date': None}

    current   = streak['current_streak']
    best      = streak['best_streak']
    last_date = streak['last_active_date']

    if is_rest_day:
        # Rest day — do nothing, preserve streak as-is
        pass
    elif fully_complete:
        if last_date == today:
            pass  # already counted today
        else:
            # Find the last non-rest day before today
            last_active_day = _get_last_active_day(user_id, today)
            if last_date == last_active_day:
                # Previous workout day was completed — extend streak
                current += 1
            elif last_date is None:
                current = 1
            else:
                # Gap in workout days (missed a non-rest day)
                current = 1
            last_date = today
    # else: today has exercises but not all done — don't reset, just don't increment

    best = max(best, current)

    with db.cursor() as cur:
        cur.execute(
            "UPDATE streak SET current_streak=%s, best_streak=%s, last_active_date=%s WHERE user_id=%s",
            (current, best, last_date, user_id)
        )

    return {'current_streak': current, 'best_streak': best, 'last_active_date': last_date}


def _get_last_active_day(user_id, before_date):
    """
    Return the most recent date before `before_date` that had at least
    one exercise scheduled (i.e. was not a rest day).
    """
    sql = """
        SELECT MAX(log_date) AS last_day
        FROM daily_log
        WHERE user_id = %s AND log_date < %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, before_date))
        row = cur.fetchone()
    return row['last_day'] if row and row['last_day'] else None


def _create_streak(user_id):
    sql = "INSERT IGNORE INTO streak (user_id, current_streak, best_streak) VALUES (%s, 0, 0)"
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
