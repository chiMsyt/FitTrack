# views/dashboard.py
# =============================================================================
# Dashboard view — the first page the user sees on launch.
#
# Responsibilities:
#   - Display 4 KPI metric cards (streak, done/total, burned, net calories)
#   - Show a contextual reminder banner (updated by ReminderScheduler)
#   - Render today's exercise routine with toggleable checkboxes
#   - Show a 7-day streak strip
#   - Embed the weekly calorie bar chart
#   - Trigger streak refresh and today-log seeding on load
#
# Data flow:
#   on_show() is called by App every time the user navigates here.
#   It re-fetches all data from the model layer and rebuilds dynamic
#   sections. Static sections (layout frames) are built once in __init__.
#
# The dashboard never writes to the DB directly — it delegates all
# mutations to model functions and then calls _refresh_metrics() to
# update the display.
# =============================================================================

import os
from datetime import date, timedelta

import customtkinter as ctk

from models.exercise  import get_today_exercises, get_total_calories_burned_today
from models.daily_log import ensure_today_logs, toggle_completion, get_heatmap_data
from models.food_entry import get_total_consumed_today, get_weekly_calorie_trend
from models.streak    import refresh_streak
from models.user      import get_user

from components.widgets import (
    SectionCard, MetricCard, MetricRow, ReminderBanner,
    ExerciseRow, ProgressBar, DayStrip, ScrollableList,
)
from utils.charts   import WeeklyCalorieBarChart
from utils.reminder import get_reminder_message, ReminderScheduler

_ACCENT   = "#1D9E75"
_WARN     = "#BA7517"
_TEXT_SEC = "#888880"
_CARD     = "#222220"


class DashboardView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", "#1A1A1A")
        super().__init__(parent, **kwargs)

        self._user_id  = user_id
        self._toast    = toast
        self._reminder_scheduler: ReminderScheduler | None = None

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout (built once)
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        # ── Page header ───────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 0))

        self._greeting_label = ctk.CTkLabel(
            header,
            text="Good morning 👋",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color="#EBEBEA",
            anchor="w",
        )
        self._greeting_label.pack(side="left")

        self._date_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont("Arial", size=12),
            text_color=_TEXT_SEC,
            anchor="e",
        )
        self._date_label.pack(side="right")

        # ── Reminder banner ───────────────────────────────────────────
        self._banner = ReminderBanner(self, message="Loading…")
        self._banner.pack(fill="x", padx=24, pady=(12, 0))

        # ── Metric row ────────────────────────────────────────────────
        self._metrics = MetricRow(self, metrics=[
            {"label": "Streak",          "value": "—", "subtitle": "days in a row",     "value_color": _ACCENT},
            {"label": "Done today",      "value": "—", "subtitle": "exercises",          "value_color": "#EBEBEA"},
            {"label": "Calories burned", "value": "—", "subtitle": "kcal estimated",     "value_color": _ACCENT},
            {"label": "Net calories",    "value": "—", "subtitle": "consumed − burned",  "value_color": _WARN},
        ])
        self._metrics.pack(fill="x", padx=24, pady=(14, 0))

        # ── Two-column section ────────────────────────────────────────
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=24, pady=(14, 20))
        cols.columnconfigure(0, weight=3)
        cols.columnconfigure(1, weight=2)

        # Left col: today's routine
        left = SectionCard(cols, title="Today's routine")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._progress_bar = ProgressBar(left.body, value=0.0, label="0% complete")
        self._progress_bar.pack(fill="x", pady=(0, 8))

        self._routine_list = ScrollableList(left.body, height=280)
        self._routine_list.pack(fill="both", expand=True)

        # Right col: streak + chart
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        streak_card = SectionCard(right, title="7-day streak")
        streak_card.pack(fill="x", pady=(0, 10))

        self._streak_strip_frame = ctk.CTkFrame(streak_card.body, fg_color="transparent")
        self._streak_strip_frame.pack(fill="x")

        self._streak_label = ctk.CTkLabel(
            streak_card.body,
            text="",
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC,
            anchor="w",
        )
        self._streak_label.pack(fill="x", pady=(6, 0))

        cal_card = SectionCard(right, title="Weekly calories")
        cal_card.pack(fill="both", expand=True)

        self._cal_chart = WeeklyCalorieBarChart(cal_card.body, data=[])
        self._cal_chart.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Public — called by App on navigation
    # ------------------------------------------------------------------

    def on_show(self, tk_root=None) -> None:
        """Refresh all data and redraw the dashboard."""
        self._update_header()
        self._load_and_render(tk_root=tk_root)

    def start_reminder_scheduler(self, tk_root) -> None:
        """
        Start the background reminder timer.
        Called once by App after the first show.
        """
        if self._reminder_scheduler is None:
            self._reminder_scheduler = ReminderScheduler(
                interval_seconds=1800,      # every 30 minutes
                callback=self._update_reminder_banner,
                tk_root=tk_root,
            )
            self._reminder_scheduler.start()

    def stop_reminder_scheduler(self) -> None:
        if self._reminder_scheduler:
            self._reminder_scheduler.stop()

    # ------------------------------------------------------------------
    # Internal — data loading
    # ------------------------------------------------------------------

    def _load_and_render(self, tk_root=None) -> None:
        # 1. Fetch today's exercises
        exercises = get_today_exercises(self._user_id)

        # 2. Seed any missing log entries for today
        exercise_ids = [e["exercise_id"] for e in exercises]
        ensure_today_logs(self._user_id, exercise_ids)

        # 3. Re-fetch with completion status (ensure_today_logs may have added rows)
        exercises = get_today_exercises(self._user_id)

        # 4. Compute stats
        total     = len(exercises)
        done      = sum(1 for e in exercises if e["is_completed"])
        burned    = get_total_calories_burned_today(self._user_id)
        consumed  = get_total_consumed_today(self._user_id)
        net       = consumed - burned
        streak    = refresh_streak(self._user_id)
        cal_data  = get_weekly_calorie_trend(self._user_id)

        # 5. Build active-days set for streak strip (past 7 days)
        heatmap   = get_heatmap_data(self._user_id)
        active_days = {
            row["log_date"] if isinstance(row["log_date"], date)
            else date.fromisoformat(str(row["log_date"]))
            for row in heatmap if row["was_active"]
        }

        # 6. Update all UI sections
        self._update_metrics(streak["current_streak"], done, total, burned, net)
        self._update_reminder_banner(done=done, total=total,
                                     streak=streak["current_streak"])
        self._render_routine(exercises)
        self._render_streak_strip(active_days)
        self._streak_label.configure(
            text=f"🔥 {streak['current_streak']}-day streak  ·  Best: {streak['best_streak']}"
        )
        self._cal_chart.refresh(cal_data)

    # ------------------------------------------------------------------
    # Internal — UI updates
    # ------------------------------------------------------------------

    def _update_header(self) -> None:
        today = date.today()
        hour  = __import__("datetime").datetime.now().hour

        if hour < 12:
            greeting = "Good morning 👋"
        elif hour < 18:
            greeting = "Good afternoon 👋"
        else:
            greeting = "Good evening 👋"

        self._greeting_label.configure(text=greeting)
        self._date_label.configure(
            text=today.strftime("%A, %B %d, %Y").replace(" 0", " ")
        )

    def _update_metrics(
        self,
        streak: int,
        done: int,
        total: int,
        burned: int,
        net: int,
    ) -> None:
        pct = int(done / total * 100) if total else 0
        self._metrics.cards[0].update(str(streak))
        self._metrics.cards[1].update(f"{done} / {total}")
        self._metrics.cards[2].update(str(burned))
        net_color = _ACCENT if net <= 0 else _WARN
        self._metrics.cards[3].update(str(net), value_color=net_color)
        self._progress_bar.update(
            pct / 100,
            label=f"{pct}% complete — {done} of {total} exercises done"
        )

    def _update_reminder_banner(
        self,
        done: int = None,
        total: int = None,
        streak: int = None,
    ) -> None:
        """
        Update the reminder banner message.
        When called by ReminderScheduler (no args), re-fetches fresh data.
        """
        if done is None or total is None:
            exercises = get_today_exercises(self._user_id)
            total = len(exercises)
            done  = sum(1 for e in exercises if e["is_completed"])
        if streak is None:
            from models.streak import get_streak
            s = get_streak(self._user_id)
            streak = s["current_streak"] if s else 0

        msg = get_reminder_message(
            completed=done, total=total, current_streak=streak
        )
        self._banner.set_message(msg)

    def _render_routine(self, exercises: list[dict]) -> None:
        """Clear and rebuild the today's-routine scrollable list."""
        self._routine_list.clear()

        if not exercises:
            ctk.CTkLabel(
                self._routine_list,
                text="No exercises scheduled for today.\nAdd some in the Exercises tab.",
                font=ctk.CTkFont("Arial", size=12),
                text_color=_TEXT_SEC,
            ).pack(pady=30)
            return

        for ex in exercises:
            row = ExerciseRow(
                self._routine_list,
                exercise=ex,
                on_toggle=self._handle_toggle,
                show_check=True,
            )
            row.pack(fill="x", pady=2)

    def _render_streak_strip(self, active_days: set) -> None:
        for w in self._streak_strip_frame.winfo_children():
            w.destroy()
        strip = DayStrip(self._streak_strip_frame, active_days=active_days)
        strip.pack(fill="x")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _handle_toggle(self, exercise_id: int, new_state: bool) -> None:
        """Called when a routine checkbox is ticked or unticked."""
        success = toggle_completion(self._user_id, exercise_id, new_state)
        if success:
            action = "completed ✓" if new_state else "marked pending"
            self._toast.show(f"Exercise {action}.", kind="success" if new_state else "info")
            # Refresh metrics without rebuilding the full list
            burned   = get_total_calories_burned_today(self._user_id)
            consumed = get_total_consumed_today(self._user_id)
            exercises = get_today_exercises(self._user_id)
            total = len(exercises)
            done  = sum(1 for e in exercises if e["is_completed"])
            streak = refresh_streak(self._user_id)
            self._update_metrics(streak["current_streak"], done, total, burned, consumed - burned)
        else:
            self._toast.show("Could not update exercise.", kind="error")
