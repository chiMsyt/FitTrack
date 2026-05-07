# utils/charts.py
# =============================================================================
# Chart helpers for FitTrack — Matplotlib embedded in CustomTkinter.
#
# Why Matplotlib instead of a JS charting library?
#   FitTrack is a desktop app. Matplotlib integrates directly with tkinter
#   via FigureCanvasTkAgg, which renders a Figure into any Frame widget
#   with no browser or webview required.
#
# Architecture:
#   Each function builds and returns a ChartFrame (CTkFrame subclass) that
#   can be .pack()ed or .grid()ed anywhere in the view layer. The view
#   never imports matplotlib directly — all chart configuration is here.
#
#   When data changes (e.g., after an exercise is completed), the view
#   calls chart.refresh(new_data) to redraw without rebuilding the widget.
#
# Shared style settings are applied once in _apply_dark_style() to keep
# all charts visually consistent with the FitTrack dark theme.
# =============================================================================

import tkinter as tk
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")   # must be set before importing pyplot

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import date, timedelta


# ── Shared colour palette (mirrors widgets.py tokens) ────────────────────────
_BG       = "#1A1A1A"
_CARD     = "#222220"
_ACCENT   = "#1D9E75"
_WARN     = "#BA7517"
_DANGER   = "#A32D2D"
_TEXT_PRI = "#EBEBEA"
_TEXT_SEC = "#888880"
_DIVIDER  = "#2C2C2A"
_GRID_CLR = "#2C2C2A"

_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _apply_dark_style(fig: Figure, ax) -> None:
    """Apply FitTrack dark theme to any matplotlib Figure + Axes pair."""
    fig.patch.set_facecolor(_CARD)
    ax.set_facecolor(_CARD)
    ax.tick_params(colors=_TEXT_SEC, labelsize=9)
    ax.xaxis.label.set_color(_TEXT_SEC)
    ax.yaxis.label.set_color(_TEXT_SEC)
    for spine in ax.spines.values():
        spine.set_edgecolor(_DIVIDER)
    ax.grid(color=_GRID_CLR, linewidth=0.5, axis="y")
    ax.grid(False, axis="x")


# =============================================================================
# ChartFrame base — wraps a Figure + Canvas in a CTkFrame
# =============================================================================

class ChartFrame(ctk.CTkFrame):
    """
    Base class for all chart widgets.
    Subclasses call _init_canvas() once to create the figure,
    then override refresh() to redraw with new data.
    """

    def __init__(self, parent, figsize=(5, 2.6), **kwargs):
        kwargs.setdefault("fg_color",      _CARD)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)

        self._fig = Figure(figsize=figsize, dpi=96)
        self._ax  = self._fig.add_subplot(111)
        _apply_dark_style(self._fig, self._ax)

        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def _redraw(self) -> None:
        """Flush the canvas after updating axes data."""
        self._fig.tight_layout(pad=0.8)
        self._canvas.draw()

    def refresh(self, *args, **kwargs) -> None:
        """Override in subclasses to accept new data and redraw."""
        raise NotImplementedError


# =============================================================================
# WeeklyCalorieBarChart
# =============================================================================

class WeeklyCalorieBarChart(ChartFrame):
    """
    Bar chart: net calories per day for the past 7 days.
    Data source: food_entry.get_weekly_calorie_trend()
    """

    def __init__(self, parent, data: list[dict] = None, **kwargs):
        super().__init__(parent, figsize=(4.8, 2.2), **kwargs)
        self.refresh(data or [])

    def refresh(self, data: list[dict]) -> None:
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)

        today  = date.today()
        monday = today - timedelta(days=today.weekday())
        labels  = _DAY_LABELS
        values  = [0] * 7

        for row in data:
            d = row.get("entry_date")
            if isinstance(d, str):
                from datetime import datetime
                d = datetime.strptime(d, "%Y-%m-%d").date()
            if d:
                idx = (d - monday).days
                if 0 <= idx < 7:
                    values[idx] = int(row.get("net_calories", 0))

        colors = [_ACCENT if v >= 0 else _DANGER for v in values]
        bars   = self._ax.bar(labels, values, color=colors, width=0.55)

        # Colour today's bar slightly brighter
        today_idx = today.weekday()
        if 0 <= today_idx < 7:
            bars[today_idx].set_edgecolor(_TEXT_PRI)
            bars[today_idx].set_linewidth(1.5)

        self._ax.axhline(0, color=_DIVIDER, linewidth=0.8)
        self._ax.set_ylabel("Net kcal", fontsize=9)
        self._redraw()


# =============================================================================
# WeeklyVolumeBarChart
# =============================================================================

class WeeklyVolumeBarChart(ChartFrame):
    """
    Bar chart: number of exercises scheduled per day of the week.
    Data source: exercise.get_weekly_volume()
    """

    _DAY_ORDER = {d: i for i, d in enumerate(_DAY_LABELS + ["Daily"])}

    def __init__(self, parent, data: list[dict] = None, **kwargs):
        super().__init__(parent, figsize=(6, 2.8), **kwargs)
        self.refresh(data or [])

    def refresh(self, data: list[dict]) -> None:
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)

        counts = {d: 0 for d in _DAY_LABELS}
        for row in data:
            day   = row.get("scheduled_day", "")
            count = int(row.get("exercise_count", 0))
            if day == "Daily":
                for k in counts:
                    counts[k] += count
            elif day in counts:
                counts[day] += count

        labels = _DAY_LABELS
        values = [counts[d] for d in labels]

        self._ax.bar(labels, values, color=_ACCENT, width=0.5)
        self._ax.set_ylabel("Exercises", fontsize=9)
        self._ax.yaxis.set_major_locator(
            matplotlib.ticker.MaxNLocator(integer=True)
        )
        self._redraw()


# =============================================================================
# CompletionLineChart
# =============================================================================

class CompletionLineChart(ChartFrame):
    """
    Line chart: daily completion % over the past 7 days.
    Data source: daily_log.get_weekly_completion()
    """

    def __init__(self, parent, data: list[dict] = None, **kwargs):
        super().__init__(parent, figsize=(5.2, 2.6), **kwargs)
        self.refresh(data or [])

    def refresh(self, data: list[dict]) -> None:
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)

        today  = date.today()
        monday = today - timedelta(days=today.weekday())
        labels = _DAY_LABELS
        rates  = [None] * 7

        for row in data:
            d = row.get("log_date")
            if isinstance(d, str):
                from datetime import datetime
                d = datetime.strptime(d, "%Y-%m-%d").date()
            if d:
                idx = (d - monday).days
                if 0 <= idx < 7:
                    rates[idx] = float(row.get("completion_rate", 0))

        # Only plot days that have data
        plot_x = [labels[i] for i, r in enumerate(rates) if r is not None]
        plot_y = [r         for r in rates if r is not None]

        if plot_x:
            self._ax.plot(
                plot_x, plot_y,
                color=_ACCENT,
                linewidth=2,
                marker="o",
                markersize=5,
                markerfacecolor=_ACCENT,
            )
            self._ax.fill_between(
                plot_x, plot_y, alpha=0.12, color=_ACCENT
            )

        self._ax.set_ylim(0, 105)
        self._ax.set_ylabel("Completion %", fontsize=9)
        self._ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v)}%")
        )
        self._redraw()


# =============================================================================
# CalorieDonutChart
# =============================================================================

class CalorieDonutChart(ChartFrame):
    """
    Donut chart: calories consumed vs remaining vs over-budget.
    Updates via refresh(consumed, goal).
    """

    def __init__(self, parent, consumed: int = 0, goal: int = 2000, **kwargs):
        super().__init__(parent, figsize=(3.2, 2.8), **kwargs)
        self.refresh(consumed, goal)

    def refresh(self, consumed: int, goal: int) -> None:
        self._ax.clear()
        self._fig.patch.set_facecolor(_CARD)
        self._ax.set_facecolor(_CARD)

        remaining = max(0, goal - consumed)
        over      = max(0, consumed - goal)

        if consumed == 0:
            sizes  = [1]
            colors = [_DIVIDER]
        elif over > 0:
            sizes  = [goal, over]
            colors = [_WARN, _DANGER]
        else:
            sizes  = [consumed, remaining]
            colors = [_WARN, "#282826"]

        wedges, _ = self._ax.pie(
            sizes,
            colors=colors,
            startangle=90,
            wedgeprops={"width": 0.42, "edgecolor": _CARD, "linewidth": 2},
        )

        # Centre label
        label = f"{consumed}\nkcal"
        self._ax.text(
            0, 0, label,
            ha="center", va="center",
            fontsize=12, fontweight="bold",
            color=_TEXT_PRI,
        )

        self._canvas.draw()
