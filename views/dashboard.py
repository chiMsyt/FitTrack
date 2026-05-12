# views/dashboard.py
import customtkinter as ctk
from datetime import date

from models.exercise   import get_today_exercises, get_total_calories_burned_today
from models.daily_log  import ensure_today_logs, get_heatmap_data
from models.food_entry import get_total_consumed_today, get_weekly_calorie_trend
from models.streak     import refresh_streak, get_streak
from models.user       import get_user

from components.widgets import (
    SectionCard, MetricRow, ReminderBanner, ProgressBar, DayStrip,
)
from utils.charts   import WeeklyCalorieBarChart
from utils.reminder import get_reminder_message, ReminderScheduler

_ACCENT   = "#1D9E75"
_WARN     = "#BA7517"
_TEXT_SEC = "#888880"
_TEXT_TER = "#555550"
_DIVIDER  = "#2C2C2A"


class DashboardView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", "#1A1A1A")
        super().__init__(parent, **kwargs)
        self._user_id  = user_id
        self._toast    = toast
        self._reminder_scheduler = None
        self._build_layout()

    def _build_layout(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        self._greeting_label = ctk.CTkLabel(
            hdr, text="Good morning 👋",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color="#EBEBEA", anchor="w",
        )
        self._greeting_label.pack(side="left")
        self._date_label = ctk.CTkLabel(
            hdr, text="", font=ctk.CTkFont("Arial", size=12),
            text_color=_TEXT_SEC, anchor="e",
        )
        self._date_label.pack(side="right")

        # Reminder banner
        self._banner = ReminderBanner(self, message="Loading…")
        self._banner.pack(fill="x", padx=24, pady=(12, 0))

        # KPI metrics
        self._metrics = MetricRow(self, metrics=[
            {"label": "Streak",          "value": "—", "subtitle": "days in a row",    "value_color": _ACCENT},
            {"label": "Done today",      "value": "—", "subtitle": "exercises",         "value_color": "#EBEBEA"},
            {"label": "Calories burned", "value": "—", "subtitle": "kcal estimated",    "value_color": _ACCENT},
            {"label": "Net calories",    "value": "—", "subtitle": "consumed − burned", "value_color": _WARN},
        ])
        self._metrics.pack(fill="x", padx=24, pady=(14, 0))

        # Today's progress (compact — no list; routine lives in Weekly Plan)
        prog_card = SectionCard(self, title="Today's progress")
        prog_card.pack(fill="x", padx=24, pady=(12, 0))
        self._progress_bar = ProgressBar(prog_card.body, value=0.0, label="0% complete")
        self._progress_bar.pack(fill="x")
        self._progress_hint = ctk.CTkLabel(
            prog_card.body,
            text="Head to the Weekly Plan tab to check off today's exercises.",
            font=ctk.CTkFont("Arial", size=11), text_color=_TEXT_TER, anchor="w",
        )
        self._progress_hint.pack(fill="x", pady=(4, 0))

        # Two-column lower section
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=24, pady=(12, 20))
        cols.columnconfigure(0, weight=3)
        cols.columnconfigure(1, weight=2)

        # Left — streak strip + quick stats
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        streak_card = SectionCard(left, title="This week's streak")
        streak_card.pack(fill="x", pady=(0, 10))
        self._streak_strip_frame = ctk.CTkFrame(streak_card.body, fg_color="transparent")
        self._streak_strip_frame.pack(fill="x")
        self._streak_label = ctk.CTkLabel(
            streak_card.body, text="",
            font=ctk.CTkFont("Arial", size=11), text_color=_TEXT_SEC, anchor="w",
        )
        self._streak_label.pack(fill="x", pady=(6, 0))

        stats_card = SectionCard(left, title="Today at a glance")
        stats_card.pack(fill="both", expand=True)
        self._stats_frame = ctk.CTkFrame(stats_card.body, fg_color="transparent")
        self._stats_frame.pack(fill="x")

        # Right — weekly calorie chart
        right = SectionCard(cols, title="Weekly calories")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._cal_chart = WeeklyCalorieBarChart(right.body, data=[])
        self._cal_chart.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def on_show(self, tk_root=None) -> None:
        self._update_header()
        self._load_and_render(tk_root=tk_root)

    def start_reminder_scheduler(self, tk_root) -> None:
        if self._reminder_scheduler is None:
            self._reminder_scheduler = ReminderScheduler(
                interval_seconds=1800,
                callback=self._update_reminder_banner,
                tk_root=tk_root,
            )
            self._reminder_scheduler.start()

    def stop_reminder_scheduler(self) -> None:
        if self._reminder_scheduler:
            self._reminder_scheduler.stop()

    # ------------------------------------------------------------------
    def _load_and_render(self, tk_root=None) -> None:
        exercises = get_today_exercises(self._user_id)
        ensure_today_logs(self._user_id, [e["exercise_id"] for e in exercises])
        exercises = get_today_exercises(self._user_id)

        total    = len(exercises)
        done     = sum(1 for e in exercises if e["is_completed"])
        burned   = get_total_calories_burned_today(self._user_id)
        consumed = get_total_consumed_today(self._user_id)
        streak   = refresh_streak(self._user_id)
        cal_data = get_weekly_calorie_trend(self._user_id)

        heatmap = get_heatmap_data(self._user_id)
        active_days = {
            (row["log_date"] if isinstance(row["log_date"], date)
             else date.fromisoformat(str(row["log_date"])))
            for row in heatmap if row["was_active"]
        }

        self._update_metrics(streak["current_streak"], done, total, burned, consumed - burned)
        self._update_reminder_banner(done=done, total=total, streak=streak["current_streak"])
        self._render_streak_strip(active_days)
        self._render_quick_stats(exercises, consumed, burned)
        self._streak_label.configure(
            text=f"🔥 {streak['current_streak']}-day streak  ·  Best: {streak['best_streak']}"
        )
        self._cal_chart.refresh(cal_data)

    def _update_header(self) -> None:
        import datetime
        hour  = datetime.datetime.now().hour
        today = date.today()
        greeting = (
            "Good morning 👋" if hour < 12 else
            "Good afternoon 👋" if hour < 18 else
            "Good evening 👋"
        )
        self._greeting_label.configure(text=greeting)
        self._date_label.configure(
            text=today.strftime("%A, %B %d, %Y").replace(" 0", " ")
        )

    def _update_metrics(self, streak, done, total, burned, net) -> None:
        pct = int(done / total * 100) if total else 0
        self._metrics.cards[0].update(str(streak))
        self._metrics.cards[1].update(f"{done} / {total}")
        self._metrics.cards[2].update(str(burned))
        self._metrics.cards[3].update(str(net), value_color=_ACCENT if net <= 0 else _WARN)
        self._progress_bar.update(
            pct / 100,
            label=f"{pct}% complete — {done} of {total} exercises done"
        )
        self._progress_hint.configure(
            text="All done for today! 🎉" if (total > 0 and done == total)
            else "Head to the Weekly Plan tab to check off today's exercises."
        )

    def _update_reminder_banner(self, done=None, total=None, streak=None) -> None:
        if done is None or total is None:
            exercises = get_today_exercises(self._user_id)
            total = len(exercises)
            done  = sum(1 for e in exercises if e["is_completed"])
        if streak is None:
            s = get_streak(self._user_id)
            streak = s["current_streak"] if s else 0
        self._banner.set_message(
            get_reminder_message(completed=done, total=total, current_streak=streak)
        )

    def _render_streak_strip(self, active_days: set) -> None:
        for w in self._streak_strip_frame.winfo_children():
            w.destroy()
        DayStrip(self._streak_strip_frame, active_days=active_days).pack(fill="x")

    def _render_quick_stats(self, exercises, consumed, burned) -> None:
        for w in self._stats_frame.winfo_children():
            w.destroy()
        categories = {}
        for ex in exercises:
            cat = ex.get("category", "Strength")
            categories[cat] = categories.get(cat, 0) + 1
        rows = [
            ("Meals logged today",  f"{consumed} kcal consumed"),
            ("Burned today",        f"{burned} kcal"),
            ("Categories today",    ", ".join(f"{v}× {k}" for k, v in categories.items()) or "—"),
        ]
        for label, value in rows:
            r = ctk.CTkFrame(self._stats_frame, fg_color="transparent")
            r.pack(fill="x", pady=3)
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont("Arial", size=11),
                         text_color=_TEXT_SEC, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=value, font=ctk.CTkFont("Arial", size=11),
                         text_color="#EBEBEA", anchor="e").pack(side="right")
            ctk.CTkFrame(self._stats_frame, height=1, fg_color=_DIVIDER).pack(fill="x")
