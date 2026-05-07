# models/daily_log.py
# =============================================================================
# Daily log model — all SQL for the `daily_log` table.
#
# The daily_log table is the central fact table of FitTrack.
# It records which exercises were performed on which dates and whether
# they were completed. The dashboard, progress tracker, heatmap, and
# completion rate chart all source their data from this table (via views).
#
# Key design note on upsert:
#   When the user opens the app and today's routine is loaded, log entries
#   for today's exercises may not exist yet (first open of the day).
#   ensure_today_logs() handles this by inserting missing entries without
#   touching existing ones — using INSERT IGNORE to respect the unique
#   constraint (user_id, exercise_id, log_date) from BR-09.
# =============================================================================

from datetime import date

from config.db import db, DBError


# ---------------------------------------------------------------------------
# CREATE / UPSERT
# ---------------------------------------------------------------------------

def ensure_today_logs(user_id: int, exercise_ids: list[int]) -> None:
    """
    Insert a pending log entry for each exercise_id that does not yet
    have one for today. Existing entries are untouched (INSERT IGNORE).

    Called by the dashboard on load to guarantee every today-scheduled
    exercise has a corresponding log row before any toggle is attempted.
    """
    if not exercise_ids:
        return

    sql = """
        INSERT IGNORE INTO daily_log (user_id, exercise_id, log_date, is_completed)
        VALUES (%s, %s, CURRENT_DATE, 0)
    """
    with db.cursor() as cur:
        rows = [(user_id, ex_id) for ex_id in exercise_ids]
        cur.executemany(sql, rows)


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def get_log_for_today(user_id: int) -> list[dict]:
    """
    Return all log entries for the current date for a given user.
    Each dict contains: log_id, exercise_id, is_completed, completed_at.
    """
    sql = """
        SELECT log_id, exercise_id, log_date,
               is_completed, completed_at
        FROM   daily_log
        WHERE  user_id  = %s
          AND  log_date = CURRENT_DATE
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_weekly_completion(user_id: int) -> list[dict]:
    """
    Return daily completion rates for the past 7 days.
    Uses v_weekly_completion view.
    Columns: log_date, day_name, total_scheduled, total_completed,
             completion_rate (0–100 float).
    """
    sql = """
        SELECT log_date, day_name, total_scheduled,
               total_completed, completion_rate
        FROM   v_weekly_completion
        WHERE  user_id = %s
        ORDER  BY log_date ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_heatmap_data(user_id: int) -> list[dict]:
    """
    Return 30-day activity data for the heatmap.
    Uses v_30day_heatmap view.
    Columns: log_date, was_active (0|1), exercises_done (int).
    """
    sql = """
        SELECT log_date, was_active, exercises_done
        FROM   v_30day_heatmap
        WHERE  user_id = %s
        ORDER  BY log_date ASC
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id,))
        return cur.fetchall()


def get_total_completed_all_time(user_id: int) -> int:
    """
    Return total number of exercises ever marked completed by this user.
    Used on the progress page as a lifetime stat.
    """
    sql = """
        SELECT COUNT(*) AS total
        FROM   daily_log
        WHERE  user_id      = %s
          AND  is_completed  = 1
    """
    with db.cursor(dictionary=False) as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_active_days_last_30(user_id: int) -> int:
    """
    Return the count of distinct dates in the past 30 days on which
    the user completed at least one exercise. Used on progress page.
    """
    sql = """
        SELECT COUNT(DISTINCT log_date) AS active_days
        FROM   daily_log
        WHERE  user_id      = %s
          AND  is_completed  = 1
          AND  log_date     >= DATE_SUB(CURRENT_DATE, INTERVAL 29 DAY)
    """
    with db.cursor(dictionary=False) as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def toggle_completion(
    user_id: int,
    exercise_id: int,
    is_completed: bool,
) -> bool:
    """
    Set is_completed and completed_at for today's log entry.

    is_completed = True  → marks done, sets completed_at to NOW()
    is_completed = False → marks undone, clears completed_at

    Returns True if a row was updated (log entry existed), False otherwise.
    """
    if is_completed:
        sql = """
            UPDATE daily_log
            SET    is_completed = 1,
                   completed_at = NOW()
            WHERE  user_id      = %s
              AND  exercise_id  = %s
              AND  log_date     = CURRENT_DATE
        """
    else:
        sql = """
            UPDATE daily_log
            SET    is_completed = 0,
                   completed_at = NULL
            WHERE  user_id      = %s
              AND  exercise_id  = %s
              AND  log_date     = CURRENT_DATE
        """

    with db.cursor() as cur:
        cur.execute(sql, (user_id, exercise_id))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_log_entry(log_id: int, user_id: int) -> bool:
    """
    Delete a specific log entry by ID.
    user_id guard prevents cross-user deletion.
    """
    sql = """
        DELETE FROM daily_log
        WHERE  log_id   = %s
          AND  user_id  = %s
    """
    with db.cursor() as cur:
        cur.execute(sql, (log_id, user_id))
        return cur.rowcount > 0
