# views/weekly.py
import customtkinter as ctk
from datetime import date, timedelta

from components.widgets import (
    SectionCard, ExerciseRow, ScrollableList, ProgressBar,
)
from utils.charts       import WeeklyVolumeBarChart
from models.exercise    import get_exercises_by_day, get_weekly_volume, get_today_exercises
from models.daily_log   import ensure_today_logs, toggle_completion
from models.streak      import refresh_streak

_ACCENT     = "#1D9E75"
_ACCENT_DIM = "#1A3D30"
_ACCENT_TXT = "#A8F0D8"
_WARN       = "#BA7517"
_WARN_DIM   = "#3A2A08"
_WARN_TXT   = "#F5C87A"
_DANGER_DIM = "#3A0D0D"
_DANGER_TXT = "#F5A0A0"
_TEXT_PRI   = "#EBEBEA"
_TEXT_SEC   = "#888880"
_TEXT_TER   = "#555550"
_CARD       = "#222220"
_DIVIDER    = "#2C2C2A"
_BG         = "#1A1A1A"

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Category colors for day grid tiles (matches charts.py)
_CAT_COLORS = {
    "Strength":    (_ACCENT_DIM, _ACCENT_TXT),
    "Cardio":      (_WARN_DIM,   _WARN_TXT),
    "Core":        ("#1A1A3A",   "#A0A0F5"),
    "Flexibility": ("#2A1A3A",   "#C0A0F5"),
    "Full Body":   (_DANGER_DIM, _DANGER_TXT),
}


class WeeklyView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, on_navigate=None, **kwargs):
        kwargs.setdefault("fg_color", _BG)
        super().__init__(parent, **kwargs)
        self._user_id     = user_id
        self._toast       = toast
        self._on_navigate = on_navigate
        # Scrollable container so the whole page scrolls
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=_BG,
                                               scrollbar_button_color="#2C2C2A",
                                               scrollbar_button_hover_color="#3A3A38")
        self._scroll.pack(fill="both", expand=True)
        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        s = self._scroll  # shorthand
        # Header
        hdr = ctk.CTkFrame(s, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(
            hdr, text="Weekly Planner",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color=_TEXT_PRI, anchor="w",
        ).pack(side="left")
        if self._on_navigate:
            ctk.CTkButton(
                hdr, text="+ Manage exercises", width=150, height=30,
                corner_radius=7, fg_color="#2A2A28", hover_color="#3A3A38",
                font=ctk.CTkFont("Arial", size=12), text_color=_TEXT_SEC,
                command=lambda: self._on_navigate("exercises"),
            ).pack(side="right")

        # ── TODAY'S ROUTINE (interactive) ─────────────────────────────
        today_card = SectionCard(s, title="Today's routine")
        today_card.pack(fill="x", padx=24, pady=(14, 0))

        self._today_progress = ProgressBar(today_card.body, value=0.0, label="0% complete")
        self._today_progress.pack(fill="x", pady=(0, 6))

        self._today_list = ScrollableList(today_card.body, height=200)
        self._today_list.pack(fill="both", expand=True)

        # ── 7-DAY SCHEDULE GRID ───────────────────────────────────────
        grid_card = SectionCard(s, title="This week's schedule")
        grid_card.pack(fill="x", padx=24, pady=(12, 0))

        self._grid_frame = ctk.CTkFrame(grid_card.body, fg_color="transparent")
        self._grid_frame.pack(fill="x")
        for i in range(7):
            self._grid_frame.columnconfigure(i, weight=1, uniform="day")

        # ── BOTTOM: summary + chart ───────────────────────────────────
        bottom = ctk.CTkFrame(s, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=24, pady=(12, 20))
        bottom.columnconfigure(0, weight=2)
        bottom.columnconfigure(1, weight=3)

        summary_card = SectionCard(bottom, title="Daily summary")
        summary_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._summary_list = ScrollableList(summary_card.body, height=180)
        self._summary_list.pack(fill="both", expand=True)

        chart_card = SectionCard(bottom, title="Workload distribution")
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._vol_chart = WeeklyVolumeBarChart(chart_card.body, data=[])
        self._vol_chart.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh_today()
        self._refresh_week()

    # ------------------------------------------------------------------
    # Today's Routine
    # ------------------------------------------------------------------

    def _refresh_today(self) -> None:
        exercises = get_today_exercises(self._user_id)
        ensure_today_logs(self._user_id, [e["exercise_id"] for e in exercises])
        exercises = get_today_exercises(self._user_id)

        total = len(exercises)
        done  = sum(1 for e in exercises if e["is_completed"])
        pct   = int(done / total * 100) if total else 0

        self._today_progress.update(
            pct / 100,
            label=f"{pct}% — {done} of {total} done today"
        )

        self._today_list.clear()
        if not exercises:
            ctk.CTkLabel(
                self._today_list,
                text="No exercises scheduled for today. Add some in the Exercises tab.",
                font=ctk.CTkFont("Arial", size=12), text_color=_TEXT_SEC,
            ).pack(pady=20)
            return

        for ex in exercises:
            row = ExerciseRow(
                self._today_list, exercise=ex,
                on_toggle=self._handle_toggle,
                show_check=True,
            )
            row.pack(fill="x", pady=2)

    def _handle_toggle(self, exercise_id: int, new_state: bool) -> None:
        ok = toggle_completion(self._user_id, exercise_id, new_state)
        if ok:
            # Refresh streak — awards only on full completion
            streak = refresh_streak(self._user_id)
            self._refresh_today()
            action = "completed ✓" if new_state else "marked pending"
            self._toast.show(f"Exercise {action}.", kind="success" if new_state else "info")

            # Show streak notification if just awarded
            if new_state:
                exercises = get_today_exercises(self._user_id)
                total = len(exercises)
                done  = sum(1 for e in exercises if e["is_completed"])
                if total > 0 and done == total:
                    self._toast.show(
                        f"🔥 Full routine done! Streak: {streak['current_streak']} days",
                        kind="success"
                    )
        else:
            self._toast.show("Could not update exercise.", kind="error")

    # ------------------------------------------------------------------
    # Weekly grid and chart
    # ------------------------------------------------------------------

    def _refresh_week(self) -> None:
        import datetime
        today_name = datetime.date.today().strftime("%A")
        _TODAY_IDX = {
            "Monday":0,"Tuesday":1,"Wednesday":2,
            "Thursday":3,"Friday":4,"Saturday":5,"Sunday":6,
        }
        today_idx = _TODAY_IDX.get(today_name, -1)

        for w in self._grid_frame.winfo_children():
            w.destroy()

        all_day_data = {}
        for i, day in enumerate(_DAYS):
            exs = get_exercises_by_day(self._user_id, day)
            all_day_data[day] = exs
            col = self._build_day_column(day, exs, is_today=(i == today_idx))
            col.grid(row=0, column=i, sticky="nsew", padx=3, pady=4)

        self._summary_list.clear()
        for day in _DAYS:
            exs   = all_day_data[day]
            count = len(exs)
            total_cal = sum(e.get("est_calories", 0) for e in exs)
            self._build_summary_row(day, count, total_cal)

        self._vol_chart.refresh(get_weekly_volume(self._user_id))

    def _build_day_column(self, day, exercises, is_today) -> ctk.CTkFrame:
        border_color = _ACCENT if is_today else "#2E2E2C"
        header_bg    = _ACCENT_DIM if is_today else "#242422"
        header_fg    = _ACCENT_TXT if is_today else _TEXT_SEC

        col = ctk.CTkFrame(
            self._grid_frame, fg_color=_CARD, corner_radius=8,
            border_width=1, border_color=border_color,
        )
        hdr = ctk.CTkFrame(col, fg_color=header_bg, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(
            hdr, text=f"{day}{' ← today' if is_today else ''}",
            font=ctk.CTkFont("Arial", size=11, weight="bold"),
            text_color=header_fg,
        ).pack(pady=6, padx=8)

        ctk.CTkLabel(
            col, text=f"{len(exercises)} exercise{'s' if len(exercises) != 1 else ''}",
            font=ctk.CTkFont("Arial", size=10), text_color=_TEXT_TER,
        ).pack(pady=(4, 2))
        ctk.CTkFrame(col, height=1, fg_color=_DIVIDER).pack(fill="x", padx=6, pady=(0, 4))

        if not exercises:
            rest = ctk.CTkFrame(col, fg_color="#1E1E1C", corner_radius=6)
            rest.pack(fill="x", padx=6, pady=(0, 8))
            ctk.CTkLabel(rest, text="Rest day", font=ctk.CTkFont("Arial", size=10),
                         text_color=_TEXT_TER).pack(pady=8)
        else:
            for ex in exercises:
                cat = ex.get("category", "Strength")
                bg, fg = _CAT_COLORS.get(cat, (_ACCENT_DIM, _ACCENT_TXT))
                tile = ctk.CTkFrame(col, fg_color=bg, corner_radius=6)
                tile.pack(fill="x", padx=6, pady=2)
                ctk.CTkLabel(
                    tile, text=ex["name"],
                    font=ctk.CTkFont("Arial", size=10, weight="bold"),
                    text_color=fg, wraplength=90, justify="left", anchor="w",
                ).pack(fill="x", padx=6, pady=(4, 0))
                detail = f"{ex['amount']} {ex['exercise_type']} · {ex.get('est_calories',0)} kcal"
                ctk.CTkLabel(
                    tile, text=detail, font=ctk.CTkFont("Arial", size=9),
                    text_color=_TEXT_TER, anchor="w",
                ).pack(fill="x", padx=6, pady=(0, 4))
        return col

    def _build_summary_row(self, day, count, total_cal) -> None:
        row = ctk.CTkFrame(self._summary_list, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=day, font=ctk.CTkFont("Arial", size=12, weight="bold"),
                     text_color=_TEXT_PRI, width=40, anchor="w").pack(side="left", padx=(4, 10))
        label_text  = f"{count} exercise{'s' if count != 1 else ''}" if count else "Rest"
        label_color = _TEXT_SEC if count else _TEXT_TER
        ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont("Arial", size=12),
                     text_color=label_color, anchor="w").pack(side="left", fill="x", expand=True)
        if count:
            ctk.CTkLabel(row, text=f"~{total_cal} kcal", font=ctk.CTkFont("Arial", size=12),
                         text_color=_WARN, anchor="e").pack(side="right", padx=(0, 4))
        ctk.CTkFrame(self._summary_list, height=1, fg_color=_DIVIDER).pack(fill="x")
