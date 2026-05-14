# utils/charts.py
import tkinter as tk
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import date, timedelta

_BG       = "#1A1A1A"
_CARD     = "#222220"
_ACCENT   = "#1D9E75"
_WARN     = "#BA7517"
_DANGER   = "#A32D2D"
_TEXT_SEC = "#888880"
_DIVIDER  = "#2C2C2A"

_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Category colors — must match widgets.py CATEGORY_COLORS
CATEGORY_COLORS = {
    "Strength":    "#1D9E75",
    "Cardio":      "#BA7517",
    "Core":        "#5555CC",
    "Flexibility": "#8B44CC",
    "Full Body":   "#A32D2D",
}


def _apply_dark_style(fig, ax):
    fig.patch.set_facecolor(_CARD)
    ax.set_facecolor(_CARD)
    ax.tick_params(colors=_TEXT_SEC, labelsize=9)
    ax.xaxis.label.set_color(_TEXT_SEC)
    ax.yaxis.label.set_color(_TEXT_SEC)
    for spine in ax.spines.values():
        spine.set_edgecolor(_DIVIDER)
    ax.grid(color=_DIVIDER, linewidth=0.5, axis="y")
    ax.grid(False, axis="x")


class ChartFrame(ctk.CTkFrame):
    def __init__(self, parent, figsize=(5, 2.6), **kwargs):
        kwargs.setdefault("fg_color", _CARD)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)
        self._fig = Figure(figsize=figsize, dpi=96)
        self._ax  = self._fig.add_subplot(111)
        _apply_dark_style(self._fig, self._ax)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def _redraw(self):
        self._fig.tight_layout(pad=0.8)
        self._canvas.draw()

    def refresh(self, *args, **kwargs):
        raise NotImplementedError


class WeeklyCalorieBarChart(ChartFrame):
    def __init__(self, parent, data=None, **kwargs):
        super().__init__(parent, figsize=(4.8, 2.2), **kwargs)
        self.refresh(data or [])

    def refresh(self, data):
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)
        today  = date.today()
        monday = today - timedelta(days=today.weekday())
        values = [0] * 7
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
        bars = self._ax.bar(_DAY_LABELS, values, color=colors, width=0.55)
        today_idx = today.weekday()
        if 0 <= today_idx < 7:
            bars[today_idx].set_edgecolor("#EBEBEA")
            bars[today_idx].set_linewidth(1.5)
        self._ax.axhline(0, color=_DIVIDER, linewidth=0.8)
        self._ax.set_ylabel("Net kcal", fontsize=9)
        self._redraw()


class WeeklyVolumeBarChart(ChartFrame):
    """Stacked bar chart colored by exercise category."""

    def __init__(self, parent, data=None, **kwargs):
        super().__init__(parent, figsize=(6, 2.8), **kwargs)
        self.refresh(data or [])

    def refresh(self, data):
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)

        # Build dict: day -> category -> count
        day_cat: dict[str, dict[str, int]] = {d: {} for d in _DAY_LABELS}
        for row in data:
            day = row.get("scheduled_day", "")
            cat = row.get("category", "Strength")
            cnt = int(row.get("exercise_count", 0))
            targets = _DAY_LABELS if day == "Daily" else ([day] if day in day_cat else [])
            for t in targets:
                day_cat[t][cat] = day_cat[t].get(cat, 0) + cnt

        categories = list(CATEGORY_COLORS.keys())
        bottoms = [0] * 7
        for cat in categories:
            vals = [day_cat[d].get(cat, 0) for d in _DAY_LABELS]
            if any(v > 0 for v in vals):
                self._ax.bar(
                    _DAY_LABELS, vals,
                    bottom=bottoms,
                    color=CATEGORY_COLORS[cat],
                    width=0.55,
                    label=cat,
                )
                bottoms = [b + v for b, v in zip(bottoms, vals)]

        self._ax.set_ylabel("Exercises", fontsize=9)
        self._ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        if any(b > 0 for b in bottoms):
            self._ax.legend(
                fontsize=7,
                framealpha=0,
                labelcolor=_TEXT_SEC,
                loc="upper right",
            )
        self._redraw()


class CompletionLineChart(ChartFrame):
    def __init__(self, parent, data=None, **kwargs):
        super().__init__(parent, figsize=(5.2, 2.6), **kwargs)
        self.refresh(data or [])

    def refresh(self, data):
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)
        today  = date.today()
        monday = today - timedelta(days=today.weekday())
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

        # Only plot up to yesterday — today's data is incomplete
        today_idx = today.weekday()
        plot_x, plot_y, plot_colors = [], [], []
        for i, r in enumerate(rates):
            if r is not None and i < today_idx:
                plot_x.append(_DAY_LABELS[i])
                plot_y.append(r)
                plot_colors.append(_ACCENT if r >= 80 else (_WARN if r >= 50 else _DANGER))

        if not plot_x:
            self._ax.text(0.5, 0.5, "No completed days this week yet.",
                          ha="center", va="center", transform=self._ax.transAxes,
                          color=_TEXT_SEC, fontsize=10)
            self._redraw()
            return

        self._ax.plot(plot_x, plot_y, color=_ACCENT, linewidth=2.5,
                      marker="o", markersize=7, markerfacecolor=_ACCENT,
                      markeredgecolor="#EBEBEA", markeredgewidth=1)
        self._ax.fill_between(plot_x, plot_y, alpha=0.15, color=_ACCENT)

        # Color-code each point
        for i, (x, y) in enumerate(zip(plot_x, plot_y)):
            color = _ACCENT if y >= 80 else (_WARN if y >= 50 else _DANGER)
            self._ax.plot(x, y, "o", color=color, markersize=7,
                          markeredgecolor="#EBEBEA", markeredgewidth=1, zorder=5)
            self._ax.annotate(f"{int(y)}%", (x, y),
                              textcoords="offset points", xytext=(0, 8),
                              ha="center", fontsize=8, color=color)

        self._ax.set_ylim(0, 115)
        self._ax.set_ylabel("Completion %", fontsize=9)
        self._ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v)}%" if v <= 100 else "")
        )
        self._ax.axhline(100, color=_ACCENT, linewidth=0.5, linestyle="--", alpha=0.3)
        self._redraw()


class CalorieDonutChart(ChartFrame):
    """
    Two modes:
      deficit — single shrinking donut (consumed eats into goal)
      surplus — two donuts side by side:
                left:  consumed vs surplus_goal
                right: how much of surplus target has been hit
    """

    def __init__(self, parent, consumed=0, goal=2000,
                 mode="deficit", surplus_goal=None, **kwargs):
        super().__init__(parent, figsize=(3.2, 2.8), **kwargs)
        self.refresh(consumed, goal, mode, surplus_goal)

    def refresh(self, consumed, goal, mode="deficit", surplus_goal=None):
        # Clear and reset axes
        self._fig.clear()
        self._fig.patch.set_facecolor(_CARD)

        if mode == "surplus" and surplus_goal:
            self._draw_surplus(consumed, goal, surplus_goal)
        else:
            self._draw_deficit(consumed, goal)

        self._canvas.draw()

    def _draw_deficit(self, consumed, goal):
        """Single shrinking donut — remaining budget gets smaller as you eat."""
        ax = self._fig.add_subplot(111)
        ax.set_facecolor(_CARD)

        remaining = max(0, goal - consumed)
        over      = max(0, consumed - goal)

        if consumed == 0:
            sizes, colors = [1], [_DIVIDER]
        elif over > 0:
            sizes  = [goal, over]
            colors = [_WARN, _DANGER]
        else:
            # Deficit: remaining shrinks — show remaining prominently
            sizes  = [remaining, consumed]
            colors = ["#2A2A28", _WARN]   # remaining=dark, consumed=amber

        ax.pie(sizes, colors=colors, startangle=90,
               wedgeprops={"width": 0.42, "edgecolor": _CARD, "linewidth": 2})

        label = f"{remaining}\nkcal left" if over == 0 else f"-{over}\nover"
        ax.text(0, 0, label, ha="center", va="center",
                fontsize=11, fontweight="bold", color="#EBEBEA")

    def _draw_surplus(self, consumed, goal, surplus_goal):
        """Two donuts: left = intake vs goal, right = surplus hit."""
        ax1 = self._fig.add_subplot(121)
        ax2 = self._fig.add_subplot(122)

        for ax in (ax1, ax2):
            ax.set_facecolor(_CARD)

        # Left donut — intake vs calorie goal
        intake_rem = max(0, goal - consumed)
        over       = max(0, consumed - goal)
        if consumed == 0:
            s1, c1 = [1], [_DIVIDER]
        elif over > 0:
            s1, c1 = [goal, over], [_ACCENT, _WARN]
        else:
            s1, c1 = [consumed, intake_rem], [_ACCENT, "#2A2A28"]

        ax1.pie(s1, colors=c1, startangle=90,
                wedgeprops={"width": 0.42, "edgecolor": _CARD, "linewidth": 2})
        ax1.text(0, 0, f"{consumed}\nkcal", ha="center", va="center",
                 fontsize=10, fontweight="bold", color="#EBEBEA")
        ax1.set_title("Intake", fontsize=9, color=_TEXT_SEC, pad=4)

        # Right donut — how close to surplus target
        surplus_hit = max(0, consumed - goal)   # calories above maintenance
        surplus_rem = max(0, surplus_goal - surplus_hit)
        if surplus_hit == 0:
            s2, c2 = [1], [_DIVIDER]
        elif surplus_hit >= surplus_goal:
            s2, c2 = [surplus_goal, surplus_hit - surplus_goal], [_ACCENT, _WARN]
        else:
            s2, c2 = [surplus_hit, surplus_rem], [_ACCENT, "#2A2A28"]

        ax2.pie(s2, colors=c2, startangle=90,
                wedgeprops={"width": 0.42, "edgecolor": _CARD, "linewidth": 2})
        ax2.text(0, 0, f"+{surplus_hit}\nkcal", ha="center", va="center",
                 fontsize=10, fontweight="bold", color="#EBEBEA")
        ax2.set_title("Surplus", fontsize=9, color=_TEXT_SEC, pad=4)

        self._fig.tight_layout(pad=0.4)


class WeightProgressChart(ChartFrame):
    """Line chart showing max weight lifted per session over time for one exercise."""

    def __init__(self, parent, data=None, exercise_name="", **kwargs):
        super().__init__(parent, figsize=(5.5, 2.8), **kwargs)
        self.refresh(data or [], exercise_name)

    def refresh(self, data, exercise_name=""):
        self._ax.clear()
        _apply_dark_style(self._fig, self._ax)

        if not data:
            self._ax.text(0.5, 0.5, "No weight data yet.\nLog a session to start tracking.",
                          ha="center", va="center", transform=self._ax.transAxes,
                          color=_TEXT_SEC, fontsize=10)
            self._redraw()
            return

        dates   = []
        weights = []
        for row in data:
            d = row.get("log_date")
            if isinstance(d, str):
                from datetime import datetime
                d = datetime.strptime(d, "%Y-%m-%d").date()
            dates.append(d)
            weights.append(float(row.get("max_weight_kg", 0)))

        self._ax.plot(dates, weights, color=_ACCENT, linewidth=2,
                      marker="o", markersize=5, markerfacecolor=_ACCENT)
        self._ax.fill_between(dates, weights, alpha=0.10, color=_ACCENT)

        if weights:
            start, end = weights[0], weights[-1]
            gain = end - start
            sign = "+" if gain >= 0 else ""
            self._ax.annotate(
                f"{sign}{gain:.1f} kg",
                xy=(dates[-1], end),
                xytext=(8, 4), textcoords="offset points",
                fontsize=9, color=_ACCENT if gain >= 0 else _DANGER,
            )

        self._ax.set_ylabel("kg", fontsize=9)
        if exercise_name:
            self._ax.set_title(exercise_name, fontsize=10, color=_TEXT_SEC, pad=4)

        # Rotate x labels if many data points
        if len(dates) > 6:
            self._ax.tick_params(axis="x", rotation=30)

        self._redraw()
