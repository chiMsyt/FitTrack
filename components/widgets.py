# components/widgets.py
# =============================================================================
# Reusable UI widgets for FitTrack.
#
# Each class is a self-contained CTkFrame subclass.
# Views import from here — they never re-implement these patterns inline.
#
# Widgets defined:
#   - SectionCard       : titled card container (wraps content in a border box)
#   - MetricCard        : single KPI tile (label + big value + subtitle)
#   - MetricRow         : horizontal row of 4 MetricCards
#   - ReminderBanner    : coloured info bar at top of dashboard
#   - ToastManager      : stacking slide-in toast notifications
#   - ExerciseRow       : one exercise entry in a list (with check, badges, actions)
#   - FoodRow           : one food entry in the calorie log
#   - ScrollableList    : scrollable frame wrapper for variable-length lists
#   - ConfirmDialog     : blocking yes/no modal (for delete confirmations)
#   - FormModal         : base class for popup forms (exercise add/edit)
#   - ProgressBar       : labelled horizontal progress bar
#   - DayStrip          : 7-day streak visualisation strip
#   - HeatmapGrid       : 30-day activity heatmap
# =============================================================================

import tkinter as tk
import customtkinter as ctk
from datetime import date, timedelta
from typing import Callable


# ── Shared colour tokens ─────────────────────────────────────────────────────
C_BG          = "#1A1A1A"
C_CARD        = "#222220"
C_CARD_BORDER = "#2E2E2C"
C_ACCENT      = "#1D9E75"
C_ACCENT_DIM  = "#1A3D30"
C_ACCENT_TEXT = "#A8F0D8"
C_WARN        = "#BA7517"
C_WARN_DIM    = "#3A2A08"
C_WARN_TEXT   = "#F5C87A"
C_DANGER      = "#A32D2D"
C_DANGER_DIM  = "#3A0D0D"
C_DANGER_TEXT = "#F5A0A0"
C_TEXT_PRI    = "#EBEBEA"
C_TEXT_SEC    = "#888880"
C_TEXT_TER    = "#555550"
C_DIVIDER     = "#2C2C2A"
CATEGORY_COLORS = {
    "Strength":    (C_ACCENT_DIM,  C_ACCENT_TEXT),
    "Cardio":      (C_WARN_DIM,    C_WARN_TEXT),
    "Core":        ("#1A1A3A",     "#A0A0F5"),
    "Flexibility": ("#2A1A3A",     "#C0A0F5"),
    "Full Body":   (C_DANGER_DIM,  C_DANGER_TEXT),
}
MEAL_COLORS = {
    "Breakfast": ("#1A2E3A", "#7AC8F0"),
    "Lunch":     (C_ACCENT_DIM, C_ACCENT_TEXT),
    "Dinner":    ("#2A1A3A", "#C0A0F5"),
    "Snack":     (C_WARN_DIM,   C_WARN_TEXT),
}


# =============================================================================
# SectionCard
# =============================================================================

class SectionCard(ctk.CTkFrame):
    """
    Titled card container. Children should be packed into self.body.

    Usage:
        card = SectionCard(parent, title="Today's Routine")
        SomeWidget(card.body, ...).pack(...)
    """

    def __init__(self, parent, title: str = "", **kwargs):
        kwargs.setdefault("fg_color",      C_CARD)
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("border_width",  1)
        kwargs.setdefault("border_color",  C_CARD_BORDER)
        super().__init__(parent, **kwargs)

        if title:
            ctk.CTkLabel(
                self,
                text=title,
                font=ctk.CTkFont("Arial", size=13, weight="bold"),
                text_color=C_TEXT_PRI,
                anchor="w",
            ).pack(fill="x", padx=16, pady=(12, 4))

            ctk.CTkFrame(self, height=1, fg_color=C_DIVIDER).pack(
                fill="x", padx=16, pady=(0, 8)
            )

        # Public body frame — children pack here
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 12))


# =============================================================================
# MetricCard + MetricRow
# =============================================================================

class MetricCard(ctk.CTkFrame):
    """
    Single KPI tile: label on top, big value in middle, subtitle below.
    value_color accepts a hex string to colour-code the metric.
    """

    def __init__(
        self,
        parent,
        label: str,
        value: str,
        subtitle: str = "",
        value_color: str = C_TEXT_PRI,
        **kwargs,
    ):
        kwargs.setdefault("fg_color",      C_CARD)
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("border_width",  1)
        kwargs.setdefault("border_color",  C_CARD_BORDER)
        super().__init__(parent, **kwargs)

        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=ctk.CTkFont("Arial", size=10),
            text_color=C_TEXT_TER,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 0))

        self._value_label = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont("Arial", size=26, weight="bold"),
            text_color=value_color,
            anchor="w",
        )
        self._value_label.pack(fill="x", padx=14, pady=(2, 0))

        self._sub_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont("Arial", size=11),
            text_color=C_TEXT_SEC,
            anchor="w",
        )
        self._sub_label.pack(fill="x", padx=14, pady=(0, 12))

    def update(self, value: str, subtitle: str = None, value_color: str = None):
        """Live-update the displayed value without rebuilding the widget."""
        self._value_label.configure(text=value)
        if subtitle is not None:
            self._sub_label.configure(text=subtitle)
        if value_color is not None:
            self._value_label.configure(text_color=value_color)


class MetricRow(ctk.CTkFrame):
    """
    Horizontal row of MetricCard tiles.
    Pass a list of dicts with keys: label, value, subtitle, value_color.
    Access individual cards via self.cards[index].
    """

    def __init__(self, parent, metrics: list[dict], **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.cards: list[MetricCard] = []
        for i, m in enumerate(metrics):
            card = MetricCard(
                self,
                label=m.get("label", ""),
                value=str(m.get("value", "—")),
                subtitle=m.get("subtitle", ""),
                value_color=m.get("value_color", C_TEXT_PRI),
            )
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 8) if i < len(metrics) - 1 else 0)
            self.columnconfigure(i, weight=1)
            self.cards.append(card)


# =============================================================================
# ReminderBanner
# =============================================================================

class ReminderBanner(ctk.CTkFrame):
    """
    Teal info bar shown at the top of the dashboard.
    Message is updated via set_message().
    """

    def __init__(self, parent, message: str = "", **kwargs):
        kwargs.setdefault("fg_color",      C_ACCENT_DIM)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(parent, **kwargs)

        ctk.CTkLabel(
            self,
            text="🔔",
            font=ctk.CTkFont("Arial", size=14),
            text_color=C_ACCENT,
        ).pack(side="left", padx=(12, 6), pady=10)

        self._msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont("Arial", size=12),
            text_color=C_ACCENT_TEXT,
            anchor="w",
            wraplength=700,
        )
        self._msg_label.pack(side="left", fill="x", expand=True, pady=10)

    def set_message(self, message: str) -> None:
        self._msg_label.configure(text=message)


# =============================================================================
# ToastManager
# =============================================================================

class ToastManager:
    """
    Displays brief slide-in notification toasts anchored to the bottom-right
    of the root window. Toasts auto-dismiss after `duration_ms` milliseconds.

    Usage:
        toast = ToastManager(root)
        toast.show("Exercise added!")
        toast.show("Error: something failed.", kind="error")
    """

    _KINDS = {
        "success": (C_ACCENT_DIM,  C_ACCENT_TEXT,  "✓"),
        "error":   (C_DANGER_DIM,  C_DANGER_TEXT,  "✗"),
        "warning": (C_WARN_DIM,    C_WARN_TEXT,    "⚠"),
        "info":    ("#1A2030",     "#A0C8F5",      "ℹ"),
    }

    def __init__(self, root: ctk.CTk, duration_ms: int = 2800):
        self._root        = root
        self._duration_ms = duration_ms
        self._stack: list[ctk.CTkFrame] = []

    def show(self, message: str, kind: str = "success") -> None:
        bg, fg, icon = self._KINDS.get(kind, self._KINDS["info"])

        toast = ctk.CTkFrame(
            self._root,
            fg_color=bg,
            corner_radius=8,
            border_width=1,
            border_color=C_CARD_BORDER,
        )

        ctk.CTkLabel(
            toast,
            text=icon,
            font=ctk.CTkFont("Arial", size=14, weight="bold"),
            text_color=fg,
        ).pack(side="left", padx=(10, 4), pady=10)

        ctk.CTkLabel(
            toast,
            text=message,
            font=ctk.CTkFont("Arial", size=12),
            text_color=fg,
        ).pack(side="left", padx=(0, 14), pady=10)

        self._stack.append(toast)
        self._reposition()

        # Auto-dismiss
        self._root.after(self._duration_ms, lambda: self._dismiss(toast))

    def _dismiss(self, toast: ctk.CTkFrame) -> None:
        if toast in self._stack:
            self._stack.remove(toast)
        toast.place_forget()
        toast.destroy()
        self._reposition()

    def _reposition(self) -> None:
        """Stack toasts bottom-right, each 56px above the previous."""
        bottom_offset = 20
        for i, t in enumerate(reversed(self._stack)):
            t.place(relx=1.0, rely=1.0, anchor="se",
                    x=-20, y=-(bottom_offset + i * 56))
            t.lift()


# =============================================================================
# ProgressBar
# =============================================================================

class ProgressBar(ctk.CTkFrame):
    """
    Labelled horizontal progress bar.
    value: 0.0 → 1.0
    """

    def __init__(self, parent, value: float = 0.0, label: str = "", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        label_row = ctk.CTkFrame(self, fg_color="transparent")
        label_row.pack(fill="x")

        self._label = ctk.CTkLabel(
            label_row,
            text=label,
            font=ctk.CTkFont("Arial", size=11),
            text_color=C_TEXT_SEC,
            anchor="w",
        )
        self._label.pack(side="left")

        self._pct_label = ctk.CTkLabel(
            label_row,
            text=f"{int(value * 100)}%",
            font=ctk.CTkFont("Arial", size=11, weight="bold"),
            text_color=C_ACCENT,
            anchor="e",
        )
        self._pct_label.pack(side="right")

        self._bar = ctk.CTkProgressBar(
            self,
            height=8,
            corner_radius=4,
            progress_color=C_ACCENT,
            fg_color=C_CARD_BORDER,
        )
        self._bar.pack(fill="x", pady=(4, 0))
        self._bar.set(value)

    def update(self, value: float, label: str = None) -> None:
        clamped = max(0.0, min(1.0, value))
        self._bar.set(clamped)
        self._pct_label.configure(text=f"{int(clamped * 100)}%")
        if label is not None:
            self._label.configure(text=label)


# =============================================================================
# ScrollableList
# =============================================================================

class ScrollableList(ctk.CTkScrollableFrame):
    """
    Thin wrapper around CTkScrollableFrame with FitTrack colours.
    Views pack rows directly into this widget.
    """

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color",       C_CARD)
        kwargs.setdefault("corner_radius",  0)
        kwargs.setdefault("scrollbar_button_color", C_CARD_BORDER)
        kwargs.setdefault("scrollbar_button_hover_color", C_TEXT_TER)
        super().__init__(parent, **kwargs)
        # Prevent scroll events from bubbling to any parent scroll frame
        self._bind_scroll_block(self._parent_canvas)

    def _bind_scroll_block(self, widget) -> None:
        """Bind scroll-stop on the internal canvas so parent frames don't steal it."""
        def _block(e):
            widget.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"
        def _block_linux_up(e):
            widget.yview_scroll(-1, "units")
            return "break"
        def _block_linux_down(e):
            widget.yview_scroll(1, "units")
            return "break"
        widget.bind("<MouseWheel>", _block, add=True)
        widget.bind("<Button-4>",   _block_linux_up, add=True)
        widget.bind("<Button-5>",   _block_linux_down, add=True)

    def clear(self) -> None:
        """Destroy all child widgets — call before re-rendering a list."""
        for w in self.winfo_children():
            w.destroy()


# =============================================================================
# ExerciseRow
# =============================================================================

class ExerciseRow(ctk.CTkFrame):
    """
    One row in the exercise list.

    Displays: checkbox, name, amount+type, muscle group, category badge,
              scheduled day tag, edit button, delete button.

    Callbacks:
        on_toggle(exercise_id, new_bool)
        on_edit(exercise_id)
        on_delete(exercise_id)
    """

    def __init__(
        self,
        parent,
        exercise: dict,
        on_toggle:  Callable = None,
        on_edit:    Callable = None,
        on_delete:  Callable = None,
        show_check: bool = True,
        **kwargs,
    ):
        kwargs.setdefault("fg_color",      C_CARD)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(parent, **kwargs)

        ex_id       = exercise["exercise_id"]
        is_done     = bool(exercise.get("is_completed", False))
        cat         = exercise.get("category", "Strength")
        diff_bg, diff_fg = CATEGORY_COLORS.get(cat, (C_ACCENT_DIM, C_ACCENT_TEXT))
        day_tag     = exercise.get("scheduled_day", "Daily")
        name_color  = C_TEXT_TER if is_done else C_TEXT_PRI

        # ── Checkbox ─────────────────────────────────────────────────
        if show_check:
            self._check_var = tk.BooleanVar(value=is_done)
            cb = ctk.CTkCheckBox(
                self,
                text="",
                width=20,
                variable=self._check_var,
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=9,
                fg_color=C_ACCENT,
                hover_color=C_ACCENT_DIM,
                border_color=C_CARD_BORDER,
                command=lambda: on_toggle and on_toggle(
                    ex_id, self._check_var.get()
                ),
            )
            cb.pack(side="left", padx=(10, 6), pady=10)

        # ── Name + detail ─────────────────────────────────────────────
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)

        name_text = exercise.get("name", "")
        if is_done:
            name_text = f"̶{name_text}̶"  # strikethrough via combining char (best-effort)

        ctk.CTkLabel(
            info,
            text=exercise.get("name", ""),
            font=ctk.CTkFont("Arial", size=13, weight="bold"),
            text_color=C_TEXT_TER if is_done else C_TEXT_PRI,
            anchor="w",
        ).pack(fill="x")

        detail = (
            f"{exercise.get('amount', '')} {exercise.get('exercise_type', '')}"
            + (f"  ·  {exercise.get('target_muscle', '')}" if exercise.get("target_muscle") else "")
            + f"  ·  ~{exercise.get('est_calories', 0)} kcal"
        )
        ctk.CTkLabel(
            info,
            text=detail,
            font=ctk.CTkFont("Arial", size=11),
            text_color=C_TEXT_TER,
            anchor="w",
        ).pack(fill="x")

        # ── Badges ────────────────────────────────────────────────────
        badges = ctk.CTkFrame(self, fg_color="transparent")
        badges.pack(side="left", padx=8, pady=8)

        # Difficulty badge
        cat_badge = ctk.CTkFrame(badges, fg_color=diff_bg, corner_radius=6)
        cat_badge.pack(pady=(0, 4))
        ctk.CTkLabel(
            cat_badge,
            text=cat,
            font=ctk.CTkFont("Arial", size=10),
            text_color=diff_fg,
        ).pack(padx=8, pady=2)

        # Day tag
        day_badge = ctk.CTkFrame(badges, fg_color="#282826", corner_radius=6)
        day_badge.pack()
        ctk.CTkLabel(
            day_badge,
            text=day_tag,
            font=ctk.CTkFont("Arial", size=10),
            text_color=C_TEXT_SEC,
        ).pack(padx=8, pady=2)

        # ── Action buttons ────────────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="right", padx=(0, 10))

        if on_edit:
            ctk.CTkButton(
                actions,
                text="Edit",
                width=50,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont("Arial", size=11),
                fg_color="#2A2A28",
                hover_color="#3A3A38",
                text_color=C_TEXT_SEC,
                command=lambda: on_edit(ex_id),
            ).pack(pady=(0, 4))

        if on_delete:
            ctk.CTkButton(
                actions,
                text="Del",
                width=50,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont("Arial", size=11),
                fg_color=C_DANGER_DIM,
                hover_color="#4A1010",
                text_color=C_DANGER_TEXT,
                command=lambda: on_delete(ex_id),
            ).pack()

        # Bottom divider
        ctk.CTkFrame(self, height=1, fg_color=C_DIVIDER).pack(
            fill="x", side="bottom"
        )


# =============================================================================
# FoodRow
# =============================================================================

class FoodRow(ctk.CTkFrame):
    """
    One row in the food log.
    Displays: meal badge, food name, calorie amount, delete button.
    """

    def __init__(
        self,
        parent,
        entry: dict,
        on_delete: Callable = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color",      C_CARD)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(parent, **kwargs)

        entry_id = entry["entry_id"]
        meal     = entry.get("meal_type", "Snack")
        meal_bg, meal_fg = MEAL_COLORS.get(meal, (C_ACCENT_DIM, C_ACCENT_TEXT))

        # Meal badge
        badge_frame = ctk.CTkFrame(self, fg_color=meal_bg, corner_radius=6)
        badge_frame.pack(side="left", padx=(10, 8), pady=10)
        ctk.CTkLabel(
            badge_frame,
            text=meal,
            font=ctk.CTkFont("Arial", size=10),
            text_color=meal_fg,
        ).pack(padx=8, pady=3)

        # Food name
        ctk.CTkLabel(
            self,
            text=entry.get("food_name", ""),
            font=ctk.CTkFont("Arial", size=13),
            text_color=C_TEXT_PRI,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        # Calorie count
        ctk.CTkLabel(
            self,
            text=f"{entry.get('calories_kcal', 0)} kcal",
            font=ctk.CTkFont("Arial", size=13, weight="bold"),
            text_color=C_WARN_TEXT,
        ).pack(side="left", padx=12)

        # Delete button
        if on_delete:
            ctk.CTkButton(
                self,
                text="✕",
                width=28,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont("Arial", size=11),
                fg_color=C_DANGER_DIM,
                hover_color="#4A1010",
                text_color=C_DANGER_TEXT,
                command=lambda: on_delete(entry_id),
            ).pack(side="right", padx=(0, 10), pady=10)

        ctk.CTkFrame(self, height=1, fg_color=C_DIVIDER).pack(
            fill="x", side="bottom"
        )


# =============================================================================
# DayStrip — 7-day streak visualiser
# =============================================================================

class DayStrip(ctk.CTkFrame):
    """
    Horizontal strip of 7 day tiles showing active/missed/today status.
    active_days: set of date objects that were active.
    """

    _DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def __init__(self, parent, active_days: set = None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self._active_days = active_days or set()
        self._build()

    def _build(self) -> None:
        today     = date.today()
        # Align to Monday of the current week
        monday    = today - timedelta(days=today.weekday())

        for i, label in enumerate(self._DAY_LABELS):
            day_date = monday + timedelta(days=i)
            is_today  = day_date == today
            is_active = day_date in self._active_days
            is_future = day_date > today

            if is_future:
                bg = "#1E1E1C"
                fg = C_TEXT_TER
            elif is_today and is_active:
                bg = C_ACCENT
                fg = "#FFFFFF"
            elif is_today:
                bg = C_ACCENT_DIM
                fg = C_ACCENT
            elif is_active:
                bg = C_ACCENT
                fg = "#FFFFFF"
            else:
                bg = "#282826"
                fg = C_TEXT_TER

            col = ctk.CTkFrame(self, fg_color="transparent")
            col.grid(row=0, column=i, padx=3)

            tile = ctk.CTkFrame(col, width=36, height=36, corner_radius=8, fg_color=bg)
            tile.pack()
            tile.pack_propagate(False)
            ctk.CTkLabel(
                tile,
                text=label[0],   # single letter
                font=ctk.CTkFont("Arial", size=12, weight="bold"),
                text_color=fg,
            ).pack(expand=True)

            ctk.CTkLabel(
                col,
                text=label,
                font=ctk.CTkFont("Arial", size=10),
                text_color=C_TEXT_TER,
            ).pack(pady=(3, 0))


# =============================================================================
# HeatmapGrid — 30-day activity heatmap
# =============================================================================

class HeatmapGrid(ctk.CTkFrame):
    """
    5-row × 6-column grid of coloured tiles representing 30 days of activity.
    heatmap_data: list of dicts with keys 'log_date' and 'exercises_done'.
    Tiles are coloured by activity intensity.
    """

    def __init__(self, parent, heatmap_data: list[dict] = None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self._data = {
            row["log_date"]: row["exercises_done"]
            for row in (heatmap_data or [])
        }
        self._build()

    def _build(self) -> None:
        today  = date.today()
        start  = today - timedelta(days=29)

        for i in range(30):
            day     = start + timedelta(days=i)
            count   = self._data.get(day, 0)
            is_today = day == today

            # Colour intensity based on exercise count
            if is_today and count == 0:
                bg = C_ACCENT_DIM
            elif count == 0:
                bg = "#232321"
            elif count <= 2:
                bg = "#0D5C40"
            elif count <= 4:
                bg = "#1D9E75"
            else:
                bg = "#5EFFC0"

            row_i = i // 6
            col_i = i % 6

            tile = ctk.CTkFrame(
                self,
                width=28, height=28,
                corner_radius=5,
                fg_color=bg,
            )
            tile.grid(row=row_i, column=col_i, padx=2, pady=2)

            # Tooltip-style: day number inside tile
            ctk.CTkLabel(
                tile,
                text=str(day.day),
                font=ctk.CTkFont("Arial", size=8),
                text_color="#FFFFFF" if count > 0 or is_today else C_TEXT_TER,
            ).pack(expand=True)


# =============================================================================
# ConfirmDialog
# =============================================================================

class ConfirmDialog(ctk.CTkToplevel):
    """
    Blocking yes/no confirmation dialog.
    Returns True if confirmed, False if cancelled.

    Usage:
        if ConfirmDialog(root, "Delete this exercise?").result:
            ...
    """

    def __init__(self, parent, message: str, title: str = "Confirm"):
        super().__init__(parent)
        self.title(title)
        self.geometry("360x160")
        self.resizable(False, False)
        self.configure(fg_color=C_CARD)
        self.grab_set()             # blocks input to parent window
        self.result = False

        ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont("Arial", size=13),
            text_color=C_TEXT_PRI,
            wraplength=300,
        ).pack(pady=(24, 16))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack()

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=110,
            height=34,
            corner_radius=7,
            fg_color="#2A2A28",
            hover_color="#3A3A38",
            text_color=C_TEXT_SEC,
            command=self._cancel,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_row,
            text="Delete",
            width=110,
            height=34,
            corner_radius=7,
            fg_color=C_DANGER_DIM,
            hover_color="#5A1515",
            text_color=C_DANGER_TEXT,
            command=self._confirm,
        ).pack(side="left", padx=6)

        self.wait_window()  # block until window closes

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()
