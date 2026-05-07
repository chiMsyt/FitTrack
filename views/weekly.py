# views/weekly.py
# =============================================================================
# Weekly planner view — shows the full 7-day exercise schedule at a glance.
#
# Responsibilities:
#   - Render a 7-column day grid, one column per day of the week
#   - Each column lists exercises scheduled for that day (Daily + specific)
#   - Embed the WeeklyVolumeBarChart for workload distribution analysis
#   - Show a per-day summary (exercise count, estimated total kcal)
#   - "Rest day" placeholder shown for days with no exercises
#
# This view is read-only — exercise scheduling is managed in ExercisesView.
# A "Go to Exercises" shortcut button is provided at the top for convenience.
# =============================================================================

import customtkinter as ctk

from components.widgets import SectionCard, ScrollableList
from utils.charts       import WeeklyVolumeBarChart
from models.exercise    import get_exercises_by_day, get_weekly_volume

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

_DIFF_COLORS = {
    "Easy":   (_ACCENT_DIM, _ACCENT_TXT),
    "Medium": (_WARN_DIM,   _WARN_TXT),
    "Hard":   (_DANGER_DIM, _DANGER_TXT),
}

_TODAY_IDX = {
    "Monday":    0, "Tuesday": 1, "Wednesday": 2,
    "Thursday":  3, "Friday":  4, "Saturday":  5, "Sunday": 6,
}


class WeeklyView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, on_navigate=None, **kwargs):
        kwargs.setdefault("fg_color", _BG)
        super().__init__(parent, **kwargs)
        self._user_id    = user_id
        self._toast      = toast
        self._on_navigate = on_navigate   # callable to jump to exercises page
        self._build_layout()

    # ------------------------------------------------------------------
    # Layout (built once)
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        # ── Header ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            hdr, text="Weekly Planner",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color=_TEXT_PRI, anchor="w",
        ).pack(side="left")

        if self._on_navigate:
            ctk.CTkButton(
                hdr, text="+ Manage exercises",
                width=150, height=30, corner_radius=7,
                fg_color="#2A2A28", hover_color="#3A3A38",
                font=ctk.CTkFont("Arial", size=12),
                text_color=_TEXT_SEC,
                command=lambda: self._on_navigate("exercises"),
            ).pack(side="right")

        self._sub_label = ctk.CTkLabel(
            self, text="Your 7-day exercise schedule at a glance.",
            font=ctk.CTkFont("Arial", size=12),
            text_color=_TEXT_SEC, anchor="w",
        )
        self._sub_label.pack(fill="x", padx=24, pady=(4, 14))

        # ── 7-column day grid ─────────────────────────────────────────
        grid_card = SectionCard(self, title="This week's schedule")
        grid_card.pack(fill="x", padx=24, pady=(0, 12))

        self._grid_frame = ctk.CTkFrame(grid_card.body, fg_color="transparent")
        self._grid_frame.pack(fill="x")

        for i in range(7):
            self._grid_frame.columnconfigure(i, weight=1, uniform="day")

        # ── Bottom row: summary + chart ───────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        bottom.columnconfigure(0, weight=2)
        bottom.columnconfigure(1, weight=3)

        # Day summary list (left)
        summary_card = SectionCard(bottom, title="Daily summary")
        summary_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._summary_list = ScrollableList(summary_card.body, height=200)
        self._summary_list.pack(fill="both", expand=True)

        # Volume chart (right)
        chart_card = SectionCard(bottom, title="Workload distribution")
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._vol_chart = WeeklyVolumeBarChart(chart_card.body, data=[])
        self._vol_chart.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        import datetime
        today_name = datetime.date.today().strftime("%A")   # e.g. "Monday"
        today_idx  = _TODAY_IDX.get(today_name, -1)

        # Clear old grid columns
        for w in self._grid_frame.winfo_children():
            w.destroy()

        all_day_data: dict[str, list[dict]] = {}
        for i, day in enumerate(_DAYS):
            exercises = get_exercises_by_day(self._user_id, day)
            all_day_data[day] = exercises
            is_today = (i == today_idx)
            col = self._build_day_column(day, exercises, is_today)
            col.grid(row=0, column=i, sticky="nsew", padx=3, pady=4)

        # Summary list
        self._summary_list.clear()
        for day in _DAYS:
            exs   = all_day_data[day]
            count = len(exs)
            total_cal = sum(e.get("est_calories", 0) for e in exs)
            self._build_summary_row(day, count, total_cal)

        # Chart
        vol_data = get_weekly_volume(self._user_id)
        self._vol_chart.refresh(vol_data)

    def _build_day_column(
        self, day: str, exercises: list[dict], is_today: bool
    ) -> ctk.CTkFrame:
        """Build and return one day column for the grid."""

        border_color = _ACCENT if is_today else "#2E2E2C"
        header_bg    = _ACCENT_DIM if is_today else "#242422"
        header_fg    = _ACCENT_TXT if is_today else _TEXT_SEC

        col_frame = ctk.CTkFrame(
            self._grid_frame,
            fg_color=_CARD,
            corner_radius=8,
            border_width=1,
            border_color=border_color,
        )

        # Day header
        day_hdr = ctk.CTkFrame(col_frame, fg_color=header_bg, corner_radius=0)
        day_hdr.pack(fill="x")

        day_label_text = f"{day} {'← today' if is_today else ''}"
        ctk.CTkLabel(
            day_hdr,
            text=day_label_text,
            font=ctk.CTkFont("Arial", size=11, weight="bold"),
            text_color=header_fg,
        ).pack(pady=6, padx=8)

        # Exercise count sub-label
        count = len(exercises)
        ctk.CTkLabel(
            col_frame,
            text=f"{count} exercise{'s' if count != 1 else ''}",
            font=ctk.CTkFont("Arial", size=10),
            text_color=_TEXT_TER,
        ).pack(pady=(6, 2))

        ctk.CTkFrame(col_frame, height=1, fg_color=_DIVIDER).pack(
            fill="x", padx=6, pady=(0, 4)
        )

        # Exercise tiles or rest placeholder
        if not exercises:
            rest_frame = ctk.CTkFrame(col_frame, fg_color="#1E1E1C", corner_radius=6)
            rest_frame.pack(fill="x", padx=6, pady=(0, 8))
            ctk.CTkLabel(
                rest_frame,
                text="Rest day",
                font=ctk.CTkFont("Arial", size=10),
                text_color=_TEXT_TER,
            ).pack(pady=8)
        else:
            for ex in exercises:
                diff = ex.get("difficulty", "Easy")
                bg, fg = _DIFF_COLORS.get(diff, (_ACCENT_DIM, _ACCENT_TXT))

                ex_tile = ctk.CTkFrame(
                    col_frame, fg_color=bg, corner_radius=6
                )
                ex_tile.pack(fill="x", padx=6, pady=2)

                ctk.CTkLabel(
                    ex_tile,
                    text=ex["name"],
                    font=ctk.CTkFont("Arial", size=10, weight="bold"),
                    text_color=fg,
                    wraplength=90,
                    justify="left",
                    anchor="w",
                ).pack(fill="x", padx=6, pady=(4, 0))

                detail = (
                    f"{ex['amount']} {ex['exercise_type']}"
                    f" · {ex.get('est_calories', 0)} kcal"
                )
                ctk.CTkLabel(
                    ex_tile,
                    text=detail,
                    font=ctk.CTkFont("Arial", size=9),
                    text_color=_TEXT_TER,
                    anchor="w",
                ).pack(fill="x", padx=6, pady=(0, 4))

        return col_frame

    def _build_summary_row(
        self, day: str, count: int, total_cal: int
    ) -> None:
        """Append one summary row to the daily summary list."""
        row = ctk.CTkFrame(
            self._summary_list,
            fg_color="transparent",
            corner_radius=0,
        )
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(
            row,
            text=day,
            font=ctk.CTkFont("Arial", size=12, weight="bold"),
            text_color=_TEXT_PRI,
            width=40,
            anchor="w",
        ).pack(side="left", padx=(4, 10))

        if count == 0:
            label_text  = "Rest"
            label_color = _TEXT_TER
        else:
            label_text  = f"{count} exercise{'s' if count != 1 else ''}"
            label_color = _TEXT_SEC

        ctk.CTkLabel(
            row,
            text=label_text,
            font=ctk.CTkFont("Arial", size=12),
            text_color=label_color,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        if count > 0:
            ctk.CTkLabel(
                row,
                text=f"~{total_cal} kcal",
                font=ctk.CTkFont("Arial", size=12),
                text_color=_WARN,
                anchor="e",
            ).pack(side="right", padx=(0, 4))

        ctk.CTkFrame(
            self._summary_list, height=1, fg_color=_DIVIDER
        ).pack(fill="x")
