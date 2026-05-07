# utils/reminder.py
# =============================================================================
# Reminder utility for FitTrack.
#
# Responsibilities:
#   1. Generate contextual reminder messages based on time of day,
#      streak status, and today's completion progress.
#   2. Schedule a repeating in-app reminder using threading.Timer so it
#      runs without blocking the tkinter main loop.
#   3. Provide a get_reminder_message() function the dashboard calls
#      on load and refresh to populate the reminder banner.
#
# Why threading.Timer and not tkinter's .after()?
#   .after() is fine for short intervals inside widgets, but reminder.py
#   is a utility module with no direct reference to the tkinter root.
#   Using threading keeps this module decoupled from the UI layer.
#   The callback safely uses root.after(0, callback) to marshal the result
#   back onto the main thread before any tkinter update.
# =============================================================================

import threading
from datetime import datetime, time as dtime


# ---------------------------------------------------------------------------
# Message generation
# ---------------------------------------------------------------------------

# Time-of-day buckets
_MORNING   = (dtime(5,  0), dtime(11, 59))
_AFTERNOON = (dtime(12, 0), dtime(17, 59))
_EVENING   = (dtime(18, 0), dtime(21, 59))
_NIGHT     = (dtime(22, 0), dtime(23, 59))

_MORNING_MSGS = [
    "Rise and grind! Your morning workout is waiting.",
    "Good morning! Start strong — complete at least one exercise.",
    "Morning sessions set the tone for the whole day. Let's go!",
]
_AFTERNOON_MSGS = [
    "Afternoon check-in: have you moved today?",
    "Beat the afternoon slump — knock out a quick set now.",
    "You're halfway through the day. Time for a workout break!",
]
_EVENING_MSGS = [
    "Evening wind-down: finish your routine before dinner.",
    "Don't let the day end without checking off your exercises.",
    "Evening energy — use it. Complete today's routine.",
]
_NIGHT_MSGS = [
    "Still up? Light stretching counts — mark something done.",
    "Rest day or not, log tomorrow's routine before you sleep.",
    "Almost midnight — squeeze in that last exercise!",
]
_STREAK_BONUS = [
    "🔥 Streak on the line — don't break it now!",
    "🔥 You're on a roll. Keep the streak alive!",
    "🔥 One more day and the streak grows stronger.",
]
_ALL_DONE_MSGS = [
    "✅ All exercises done for today. Excellent work!",
    "✅ Today's routine complete. Rest up for tomorrow.",
    "✅ You crushed it today. See you tomorrow!",
]


def get_reminder_message(
    completed: int = 0,
    total: int = 0,
    current_streak: int = 0,
) -> str:
    """
    Return a contextual reminder string for the dashboard banner.

    Args:
        completed:       Number of exercises marked done today.
        total:           Total exercises scheduled today.
        current_streak:  User's active streak count.
    """
    # All done — celebrate
    if total > 0 and completed >= total:
        import random
        return random.choice(_ALL_DONE_MSGS)

    now = datetime.now().time()
    import random

    # Pick base message by time of day
    if _MORNING[0] <= now <= _MORNING[1]:
        base = random.choice(_MORNING_MSGS)
    elif _AFTERNOON[0] <= now <= _AFTERNOON[1]:
        base = random.choice(_AFTERNOON_MSGS)
    elif _EVENING[0] <= now <= _EVENING[1]:
        base = random.choice(_EVENING_MSGS)
    else:
        base = random.choice(_NIGHT_MSGS)

    # Append streak message if streak is meaningful
    if current_streak >= 3:
        base = base + "  " + random.choice(_STREAK_BONUS)

    # Append progress context
    if total > 0 and completed < total:
        remaining = total - completed
        base += f"  ({remaining} exercise{'s' if remaining > 1 else ''} left today)"

    return base


# ---------------------------------------------------------------------------
# Scheduled reminder (runs in background thread)
# ---------------------------------------------------------------------------

class ReminderScheduler:
    """
    Fires a callback every `interval_seconds` while the app is running.
    Designed to push reminder updates to the dashboard banner.

    Usage:
        scheduler = ReminderScheduler(
            interval_seconds=1800,       # every 30 minutes
            callback=dashboard.update_reminder_banner,
            tk_root=root,
        )
        scheduler.start()
        # On app close:
        scheduler.stop()
    """

    def __init__(
        self,
        interval_seconds: int,
        callback,          # callable with no arguments
        tk_root,           # tkinter root window (for thread-safe .after())
    ):
        self._interval  = interval_seconds
        self._callback  = callback
        self._root      = tk_root
        self._timer: threading.Timer | None = None
        self._running   = False

    def start(self) -> None:
        """Begin the reminder schedule."""
        self._running = True
        self._schedule_next()

    def stop(self) -> None:
        """Cancel any pending reminder."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._fire)
        self._timer.daemon = True   # won't block app exit
        self._timer.start()

    def _fire(self) -> None:
        """
        Called on a background thread — marshal the callback back
        onto the tkinter main thread using root.after(0, ...).
        """
        if self._running:
            self._root.after(0, self._callback)
            self._schedule_next()
