# views/progress.py
# =============================================================================
# Progress view — long-term fitness analytics page.
#
# Responsibilities:
#   - Display 4 lifetime KPI metrics: active days (30d), best streak,
#     total exercises completed, this-week completion rate
#   - Render the 30-day HeatmapGrid (DSA-224: longitudinal density)
#   - Embed the CompletionLineChart for this-week trend (DSA-224: trend)
#   - Show a per-day breakdown table for the past 7 days
#   - "Motivational state" banner that changes based on streak status
#
# All data is read-only — no mutations happen from this view.
# =============================================================================

import customtkinter as ctk
from datetime import date, timedelta

from components.widgets import (
    SectionCard, MetricRow, HeatmapGrid, ScrollableList,
)
from utils.charts    import CompletionLineChart
from models.daily_log import (
    get_weekly_completion, get_heatmap_data,
    get_total_completed_all_time, get_active_days_last_30,
)
from models.streak   import get_streak

_ACCENT     = "#1D9E75"
_ACCENT_DIM = "#1A3D30"
_ACCENT_TXT = "#A8F0D8"
_WARN       = "#BA7517"
_WARN_DIM   = "#3A2A08"
_WARN_TXT   = "#F5C87A"
_DANGER     = "#A32D2D"
_DANGER_DIM = "#3A0D0D"
_DANGER_TXT = "#F5A0A0"
_TEXT_PRI   = "#EBEBEA"
_TEXT_SEC   = "#888880"
_TEXT_TER   = "#555550"
_CARD       = "#222220"
_DIVIDER    = "#2C2C2A"
_BG         = "#1A1A1A"

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ProgressView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", _BG)
        super().__init__(parent, **kwargs)
        self._user_id = user_id
        self._toast   = toast
        self._build_layout()

    # ------------------------------------------------------------------
    # Layout (built once)
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        # ── Header ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            hdr, text="Progress Tracker",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color=_TEXT_PRI, anchor="w",
        ).pack(side="left")

        # ── Motivational state banner ──────────────────────────────────
        self._motive_banner = ctk.CTkFrame(
            self, fg_color=_ACCENT_DIM, corner_radius=8
        )
        self._motive_banner.pack(fill="x", padx=24, pady=(12, 0))

        self._motive_icon  = ctk.CTkLabel(
            self._motive_banner, text="🔥",
            font=ctk.CTkFont("Arial", size=14),
            text_color=_ACCENT,
        )
        self._motive_icon.pack(side="left", padx=(12, 6), pady=10)

        self._motive_label = ctk.CTkLabel(
            self._motive_banner, text="Loading…",
            font=ctk.CTkFont("Arial", size=12),
            text_color=_ACCENT_TXT, anchor="w",
        )
        self._motive_label.pack(side="left", fill="x", expand=True, pady=10)

        # ── KPI metric row ─────────────────────────────────────────────
        self._metrics = MetricRow(self, metrics=[
            {"label": "Active days (30d)", "value": "—", "subtitle": "days with activity",    "value_color": _ACCENT},
            {"label": "Best streak",       "value": "—", "subtitle": "consecutive days",       "value_color": _TEXT_PRI},
            {"label": "Total completed",   "value": "—", "subtitle": "exercises all time",     "value_color": _TEXT_PRI},
            {"label": "Completion rate",   "value": "—", "subtitle": "this week",              "value_color": _WARN},
        ])
        self._metrics.pack(fill="x", padx=24, pady=(14, 0))

        # ── Two-column lower section ───────────────────────────────────
        lower = ctk.CTkFrame(self, fg_color="transparent")
        lower.pack(fill="both", expand=True, padx=24, pady=(14, 20))
        lower.columnconfigure(0, weight=5)
        lower.columnconfigure(1, weight=4)

        # Left: heatmap + breakdown table
        left = ctk.CTkFrame(lower, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        heatmap_card = SectionCard(left, title="30-day activity heatmap")
        heatmap_card.pack(fill="x", pady=(0, 12))

        # Legend row
        legend = ctk.CTkFrame(heatmap_card.body, fg_color="transparent")
        legend.pack(fill="x", pady=(0, 8))
        self._build_legend(legend)

        self._heatmap_frame = ctk.CTkFrame(heatmap_card.body, fg_color="transparent")
        self._heatmap_frame.pack(anchor="w")

        # Month label below heatmap
        self._month_label = ctk.CTkLabel(
            heatmap_card.body, text="",
            font=ctk.CTkFont("Arial", size=10),
            text_color=_TEXT_TER, anchor="w",
        )
        self._month_label.pack(fill="x", pady=(4, 0))

        # 7-day breakdown table
        breakdown_card = SectionCard(left, title="This week — day breakdown")
        breakdown_card.pack(fill="both", expand=True)

        self._breakdown_list = ScrollableList(breakdown_card.body, height=160)
        self._breakdown_list.pack(fill="both", expand=True)

        # Right: completion line chart
        chart_card = SectionCard(lower, title="Completion rate — this week")
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._comp_chart = CompletionLineChart(chart_card.body, data=[])
        self._comp_chart.pack(fill="both", expand=True)

        # Chart explanation label
        ctk.CTkLabel(
            chart_card.body,
            text="Each point = % of scheduled exercises completed that day.",
            font=ctk.CTkFont("Arial", size=10),
            text_color=_TEXT_TER,
        ).pack(pady=(0, 8))

    def _build_legend(self, parent) -> None:
        """Colour legend for the heatmap."""
        items = [
            ("#232321", "No activity"),
            ("#0D5C40", "1–2 done"),
            ("#1D9E75", "3–4 done"),
            ("#5EFFC0", "5+ done"),
            (_ACCENT_DIM, "Today"),
        ]
        for bg, label in items:
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(side="left", padx=(0, 12))
            ctk.CTkFrame(f, width=12, height=12, corner_radius=3, fg_color=bg).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=10), text_color=_TEXT_TER).pack(side="left")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        streak       = get_streak(self._user_id)
        active_days  = get_active_days_last_30(self._user_id)
        total_done   = get_total_completed_all_time(self._user_id)
        weekly_comp  = get_weekly_completion(self._user_id)
        heatmap_data = get_heatmap_data(self._user_id)

        # ── Compute this-week completion rate ─────────────────────────
        if weekly_comp:
            avg_rate = sum(r["completion_rate"] for r in weekly_comp) / len(weekly_comp)
        else:
            avg_rate = 0.0

        cur_streak  = streak["current_streak"] if streak else 0
        best_streak = streak["best_streak"]    if streak else 0

        # ── KPI metrics ───────────────────────────────────────────────
        self._metrics.cards[0].update(str(active_days))
        self._metrics.cards[1].update(str(best_streak))
        self._metrics.cards[2].update(str(total_done))
        rate_color = _ACCENT if avg_rate >= 80 else (_WARN if avg_rate >= 50 else _DANGER)
        self._metrics.cards[3].update(
            f"{avg_rate:.0f}%", value_color=rate_color
        )

        # ── Motivational banner ───────────────────────────────────────
        self._update_motive_banner(cur_streak, avg_rate)

        # ── Heatmap ───────────────────────────────────────────────────
        for w in self._heatmap_frame.winfo_children():
            w.destroy()
        heatmap = HeatmapGrid(self._heatmap_frame, heatmap_data=heatmap_data)
        heatmap.pack()

        today = date.today()
        start = today - timedelta(days=29)
        self._month_label.configure(
            text=f"{start.strftime('%b %d').replace(' 0', ' ')} → {today.strftime('%b %d, %Y').replace(' 0', ' ')}"
        )

        # ── Weekly breakdown table ────────────────────────────────────
        self._breakdown_list.clear()
        self._build_breakdown_table(weekly_comp)

        # ── Completion chart ──────────────────────────────────────────
        self._comp_chart.refresh(weekly_comp)

    def _update_motive_banner(self, streak: int, avg_rate: float) -> None:
        if streak >= 14:
            bg, fg, icon, msg = (_ACCENT_DIM, _ACCENT_TXT, "🏆",
                f"Incredible — {streak}-day streak! You're building a real habit.")
        elif streak >= 7:
            bg, fg, icon, msg = (_ACCENT_DIM, _ACCENT_TXT, "🔥",
                f"One full week! {streak}-day streak and counting. Keep it up.")
        elif streak >= 3:
            bg, fg, icon, msg = (_ACCENT_DIM, _ACCENT_TXT, "💪",
                f"{streak} days in a row — the habit is forming. Don't stop now.")
        elif avg_rate >= 80:
            bg, fg, icon, msg = (_ACCENT_DIM, _ACCENT_TXT, "✅",
                "Strong completion rate this week. Consistency is key.")
        elif avg_rate >= 50:
            bg, fg, icon, msg = (_WARN_DIM, _WARN_TXT, "📈",
                "You're halfway there this week. Push for a stronger finish.")
        else:
            bg, fg, icon, msg = (_DANGER_DIM, _DANGER_TXT, "⚡",
                "Low activity this week. Even one session today counts.")

        self._motive_banner.configure(fg_color=bg)
        self._motive_icon.configure(text=icon, text_color=fg)
        self._motive_label.configure(text=msg, text_color=fg)

    def _build_breakdown_table(self, weekly_comp: list[dict]) -> None:
        """Render per-day rows for the past 7 days."""

        # Build a lookup from the DB data
        comp_map: dict[str, dict] = {}
        for row in weekly_comp:
            d = row.get("log_date")
            if hasattr(d, "strftime"):
                key = d.strftime("%a")
            else:
                from datetime import datetime
                key = datetime.strptime(str(d), "%Y-%m-%d").strftime("%a")
            comp_map[key] = row

        today   = date.today()
        monday  = today - timedelta(days=today.weekday())

        # Header row
        hdr = ctk.CTkFrame(self._breakdown_list, fg_color="transparent")
        hdr.pack(fill="x", padx=4, pady=(0, 4))
        for label, width in [("Day", 50), ("Done", 50), ("Total", 50), ("Rate", 60)]:
            ctk.CTkLabel(
                hdr, text=label, width=width,
                font=ctk.CTkFont("Arial", size=10),
                text_color=_TEXT_TER, anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(self._breakdown_list, height=1, fg_color=_DIVIDER).pack(fill="x")

        for i, day_label in enumerate(_DAYS):
            day_date = monday + timedelta(days=i)
            is_future = day_date > today
            row_data  = comp_map.get(day_label[:3], None)

            done  = int(row_data["total_completed"]) if row_data else 0
            total = int(row_data["total_scheduled"]) if row_data else 0
            rate  = float(row_data["completion_rate"]) if row_data else 0.0

            row_frame = ctk.CTkFrame(
                self._breakdown_list, fg_color="transparent"
            )
            row_frame.pack(fill="x", padx=4, pady=1)

            is_today = (day_date == today)
            day_color = _ACCENT if is_today else (_TEXT_SEC if not is_future else _TEXT_TER)

            ctk.CTkLabel(
                row_frame,
                text=f"{'→ ' if is_today else ''}{day_label}",
                width=50,
                font=ctk.CTkFont("Arial", size=12, weight="bold" if is_today else "normal"),
                text_color=day_color, anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                row_frame, text="—" if is_future else str(done),
                width=50, font=ctk.CTkFont("Arial", size=12),
                text_color=_TEXT_SEC, anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                row_frame, text="—" if is_future else str(total),
                width=50, font=ctk.CTkFont("Arial", size=12),
                text_color=_TEXT_SEC, anchor="w",
            ).pack(side="left")

            if not is_future and total > 0:
                rate_color = (
                    _ACCENT if rate >= 80
                    else _WARN if rate >= 50
                    else _DANGER
                )
                rate_text = f"{rate:.0f}%"
            else:
                rate_color = _TEXT_TER
                rate_text  = "—"

            ctk.CTkLabel(
                row_frame, text=rate_text,
                width=60, font=ctk.CTkFont("Arial", size=12, weight="bold"),
                text_color=rate_color, anchor="w",
            ).pack(side="left")

            ctk.CTkFrame(
                self._breakdown_list, height=1, fg_color=_DIVIDER
            ).pack(fill="x")
